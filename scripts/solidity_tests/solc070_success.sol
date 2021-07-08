// "SPDX-License-Identifier: UNLICENSED
pragma solidity 0.7.0;

contract solc070_failure{
    constructor() {
    }
    function get_block_num() public view returns (uint256) { return block.timestamp; }
}
