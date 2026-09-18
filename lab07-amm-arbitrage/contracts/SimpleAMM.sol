// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

interface IERC20 {
    function transferFrom(address from, address to, uint256 value) external returns (bool);
    function transfer(address to, uint256 value) external returns (bool);
    function balanceOf(address account) external view returns (uint256);
}

/// @title SimpleAMM - a constant-product liquidity pool (x * y = k).
/// @notice Stand-in for the class "DEX Alpha" / "DEX Beta" contracts. The
/// pricing maths is the Uniswap V2 formula, including the 0.3% fee.
contract SimpleAMM {
    address public immutable tokenA;   // TEST
    address public immutable tokenB;   // USDC

    uint256 public reserveA;
    uint256 public reserveB;

    uint256 public constant FEE_NUMERATOR = 997;     // 0.3% fee
    uint256 public constant FEE_DENOMINATOR = 1000;

    event LiquidityAdded(uint256 amountA, uint256 amountB, uint256 reserveA, uint256 reserveB);
    event Swap(
        address indexed trader,
        address indexed tokenIn,
        uint256 amountIn,
        address indexed tokenOut,
        uint256 amountOut,
        uint256 reserveA,
        uint256 reserveB
    );

    constructor(address _tokenA, address _tokenB) {
        tokenA = _tokenA;
        tokenB = _tokenB;
    }

    function getReserves() external view returns (uint256, uint256) {
        return (reserveA, reserveB);
    }

    /// @notice Seed the pool. Caller must approve both tokens first.
    function addLiquidity(uint256 amountA, uint256 amountB) external {
        require(IERC20(tokenA).transferFrom(msg.sender, address(this), amountA), "pull A failed");
        require(IERC20(tokenB).transferFrom(msg.sender, address(this), amountB), "pull B failed");
        reserveA += amountA;
        reserveB += amountB;
        emit LiquidityAdded(amountA, amountB, reserveA, reserveB);
    }

    /// @notice Constant-product output with the 0.3% fee applied to the input.
    /// amountOut = (amountIn * 997 * reserveOut) / (reserveIn * 1000 + amountIn * 997)
    function getAmountOut(uint256 amountIn, uint256 reserveIn, uint256 reserveOut)
        public
        pure
        returns (uint256)
    {
        require(amountIn > 0, "insufficient input");
        require(reserveIn > 0 && reserveOut > 0, "insufficient liquidity");
        uint256 amountInWithFee = amountIn * FEE_NUMERATOR;
        uint256 numerator = amountInWithFee * reserveOut;
        uint256 denominator = reserveIn * FEE_DENOMINATOR + amountInWithFee;
        return numerator / denominator;
    }

    /// @notice Quote a swap without executing it.
    function quote(address tokenIn, uint256 amountIn) external view returns (uint256) {
        require(tokenIn == tokenA || tokenIn == tokenB, "unknown token");
        return tokenIn == tokenA
            ? getAmountOut(amountIn, reserveA, reserveB)
            : getAmountOut(amountIn, reserveB, reserveA);
    }

    /// @notice Swap `amountIn` of `tokenIn` for the other token.
    /// @param minAmountOut slippage guard; the swap reverts if the pool would
    /// return less than this.
    function swap(address tokenIn, uint256 amountIn, uint256 minAmountOut)
        external
        returns (uint256 amountOut)
    {
        require(tokenIn == tokenA || tokenIn == tokenB, "unknown token");
        bool aToB = tokenIn == tokenA;
        address tokenOut = aToB ? tokenB : tokenA;

        amountOut = aToB
            ? getAmountOut(amountIn, reserveA, reserveB)
            : getAmountOut(amountIn, reserveB, reserveA);
        require(amountOut >= minAmountOut, "slippage: output below minimum");

        require(IERC20(tokenIn).transferFrom(msg.sender, address(this), amountIn), "pull failed");
        require(IERC20(tokenOut).transfer(msg.sender, amountOut), "push failed");

        if (aToB) {
            reserveA += amountIn;
            reserveB -= amountOut;
        } else {
            reserveB += amountIn;
            reserveA -= amountOut;
        }

        emit Swap(msg.sender, tokenIn, amountIn, tokenOut, amountOut, reserveA, reserveB);
    }
}
