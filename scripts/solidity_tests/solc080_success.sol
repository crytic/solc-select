// "SPDX-License-Identifier: UNLICENSED
pragma solidity 0.8.0;

contract solc080 {
    function good() public pure returns (uint256){
        return type(uint).max;
    }
}