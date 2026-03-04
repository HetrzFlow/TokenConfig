// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @title StockTokenAdapter
/// @notice Unified interface for tokenized-equity interactions across
///         Robinhood Chain, BSC and generic EVM networks. Stock tokens
///         differ from plain ERC-20s: they carry transfer restrictions,
///         issuer metadata and settlement provenance that a research
///         agent must be able to read and reason about.
/// @dev Used by the stock-analyst-agent seller runtime to resolve
///      issuer metadata and price provenance before composing reports.
interface IStockToken {
    /// @notice Tokenized-equity metadata, as registered by the issuer.
    struct EquityMetadata {
        string ticker;        // e.g. "TSLA"
        string issuer;        // e.g. "Tesla, Inc."
        string exchange;      // listing venue reference
        string cusip;         // CUSIP of the underlying security
        uint8 decimals;
        uint256 totalSupply;
        bool transferRestricted;
        address issuerWallet;
    }

    function equityMetadata() external view returns (EquityMetadata memory);
    function priceProvenance() external view returns (string memory);
}

/// @title StockTokenAdapter
/// @notice Concrete adapter that normalizes stock-token access so the
///         agent's data layer is chain-agnostic.
contract StockTokenAdapter {
    error UnsupportedChain(uint256 chainId);
    error TokenNotRegistered(address token);

    event TokenRegistered(address indexed token, string ticker, uint256 chainId);
    event ChainConfigured(uint256 indexed chainId, address registry);

    struct ChainConfig {
        address registry;
        bool enabled;
    }

    mapping(uint256 => ChainConfig) public chainConfigs;
    mapping(address => IStockToken.EquityMetadata) internal _metadata;
    mapping(address => bool) public registered;

    address public owner;

    modifier onlyOwner() {
        require(msg.sender == owner, "StockTokenAdapter: not owner");
        _;
    }

    constructor() {
        owner = msg.sender;
    }

    /// @notice Point the adapter at a chain's stock-token registry.
    function configureChain(uint256 chainId, address registry) external onlyOwner {
        chainConfigs[chainId] = ChainConfig({registry: registry, enabled: true});
        emit ChainConfigured(chainId, registry);
    }

    /// @notice Register an on-chain token so the agent can resolve it.
    function registerToken(address token, uint256 chainId) external onlyOwner {
        ChainConfig memory cfg = chainConfigs[chainId];
        if (!cfg.enabled) revert UnsupportedChain(chainId);
        IStockToken.EquityMetadata memory meta = IStockToken(token).equityMetadata();
        _metadata[token] = meta;
        registered[token] = true;
        emit TokenRegistered(token, meta.ticker, chainId);
    }

    /// @notice Agent-facing lookup: returns normalized metadata for any
    ///         registered stock token on any supported chain.
    function resolve(address token) external view returns (IStockToken.EquityMetadata memory) {
        if (!registered[token]) revert TokenNotRegistered(token);
        return _metadata[token];
    }

    /// @notice Batch resolution used by the report pipeline.
    function resolveBatch(address[] calldata tokens)
        external
        view
        returns (IStockToken.EquityMetadata[] memory out)
    {
        out = new IStockToken.EquityMetadata[](tokens.length);
        for (uint256 i = 0; i < tokens.length; i++) {
            out[i] = this.resolve(tokens[i]);
        }
    }
}
