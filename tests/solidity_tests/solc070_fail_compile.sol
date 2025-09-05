// "SPDX-License-Identifier: UNLICENSED
pragma solidity 0.7.0;

contract solc070_failure{
    constructor() public {
    }
    function get_block_num() public returns (uint256) { return now; }
}
