
pragma solidity ^0.8.24;
interface IChainLink { function execute(uint256 value, address origin) external; }
interface IChainTerminal { function receiveChain(uint256 value, address origin) external; }
contract ChainEntry {
    address public next;
    event ChainStarted(address indexed starter, uint256 value);
    event EntryExecuted(address indexed starter, uint256 value);
    event Connected(address indexed nextContract);
    function setNext(address nextContract) external { next = nextContract; emit Connected(nextContract); }
    function start(uint256 value) external {
        require(next != address(0), 'entry not connected');
        emit ChainStarted(msg.sender, value); emit EntryExecuted(msg.sender, value);
        IChainLink(next).execute(value, msg.sender);
    }
}
contract ChainLink {
    uint256 public immutable index;
    address public next;
    event Connected(address indexed nextContract);
    event LinkExecuted(uint256 indexed index, address indexed origin, uint256 value);
    constructor(uint256 linkIndex) { index = linkIndex; }
    function setNext(address nextContract) external { next = nextContract; emit Connected(nextContract); }
    function execute(uint256 value, address origin) external {
        emit LinkExecuted(index, origin, value);
        if (next != address(0)) {
            if (index == 3) IChainTerminal(next).receiveChain(value, origin);
            else IChainLink(next).execute(value, origin);
        }
    }
}
contract ChainTerminal {
    uint256 public finalValue;
    address public finalOrigin;
    event FinalReceived(address indexed origin, uint256 value);
    event ChainCompleted(address indexed origin, uint256 value);
    function receiveChain(uint256 value, address origin) external {
        finalValue = value; finalOrigin = origin;
        emit FinalReceived(origin, value); emit ChainCompleted(origin, value);
    }
}
