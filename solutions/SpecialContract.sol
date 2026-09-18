// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @title SpecialContract - the NFT-receiving contract required by Lab 6.
/// @notice Stand-in for the instructor's "special contract". It implements
/// IERC721Receiver, so it accepts NFTs sent with safeTransferFrom and records
/// who deposited what.
contract SpecialContract {
    struct Deposit {
        address collection;
        uint256 tokenId;
        address depositor;
    }

    Deposit[] public deposits;

    event NFTReceived(
        address indexed collection,
        address indexed depositor,
        uint256 indexed tokenId,
        address operator
    );

    /// @dev Returning this exact selector is what tells a compliant ERC721 that
    /// the transfer is accepted. Any other value makes safeTransferFrom revert.
    function onERC721Received(
        address operator,
        address from,
        uint256 tokenId,
        bytes calldata
    ) external returns (bytes4) {
        deposits.push(Deposit({collection: msg.sender, tokenId: tokenId, depositor: from}));
        emit NFTReceived(msg.sender, from, tokenId, operator);
        return this.onERC721Received.selector;
    }

    function depositCount() external view returns (uint256) {
        return deposits.length;
    }

    /// @notice Convenience view used by the lab script to prove the deposit.
    function depositAt(uint256 index)
        external
        view
        returns (address collection, uint256 tokenId, address depositor)
    {
        Deposit storage d = deposits[index];
        return (d.collection, d.tokenId, d.depositor);
    }
}
