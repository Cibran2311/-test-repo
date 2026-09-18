// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

interface IERC20 {
    function transferFrom(address from, address to, uint256 value) external returns (bool);
    function transfer(address to, uint256 value) external returns (bool);
}

/// @title Disperse - batch distribution of ETH and ERC20 tokens.
/// @notice Functional equivalent of the disperse.app contract, deployed here
/// because the lab's browser interface cannot be driven from a script.
/// The caller must `approve` this contract for the total amount before
/// calling `disperseToken`.
contract Disperse {
    event Dispersed(address indexed token, address indexed sender, uint256 recipients, uint256 total);

    /// @dev Pulls the whole total once, then pushes to each recipient.
    /// Cheaper than one transferFrom per recipient.
    function disperseToken(
        IERC20 token,
        address[] calldata recipients,
        uint256[] calldata values
    ) external {
        require(recipients.length == values.length, "Disperse: length mismatch");
        require(recipients.length > 0, "Disperse: no recipients");

        uint256 total = 0;
        for (uint256 i = 0; i < recipients.length; i++) {
            total += values[i];
        }
        require(token.transferFrom(msg.sender, address(this), total), "Disperse: pull failed");

        for (uint256 i = 0; i < recipients.length; i++) {
            require(token.transfer(recipients[i], values[i]), "Disperse: push failed");
        }
        emit Dispersed(address(token), msg.sender, recipients.length, total);
    }

    /// @dev Variant that transfers straight from the sender to each recipient,
    /// emitting one Transfer event per recipient with the sender as `from`.
    function disperseTokenSimple(
        IERC20 token,
        address[] calldata recipients,
        uint256[] calldata values
    ) external {
        require(recipients.length == values.length, "Disperse: length mismatch");
        uint256 total = 0;
        for (uint256 i = 0; i < recipients.length; i++) {
            require(token.transferFrom(msg.sender, recipients[i], values[i]), "Disperse: transfer failed");
            total += values[i];
        }
        emit Dispersed(address(token), msg.sender, recipients.length, total);
    }

    /// @dev Batch ETH distribution; refunds any surplus to the sender.
    function disperseEther(
        address[] calldata recipients,
        uint256[] calldata values
    ) external payable {
        require(recipients.length == values.length, "Disperse: length mismatch");
        for (uint256 i = 0; i < recipients.length; i++) {
            (bool ok, ) = recipients[i].call{value: values[i]}("");
            require(ok, "Disperse: ETH transfer failed");
        }
        uint256 balance = address(this).balance;
        if (balance > 0) {
            (bool ok, ) = msg.sender.call{value: balance}("");
            require(ok, "Disperse: refund failed");
        }
        emit Dispersed(address(0), msg.sender, recipients.length, msg.value);
    }
}
