pragma solidity 0.8.0;

contract solc080 {
    function good() public returns (uint256){
        return type(uint).max;
    }
}