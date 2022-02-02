//SPDX-License-Identifier:UNLICENSED
pragma solidity ^0.8.0;
import "https://github.com/OpenZeppelin/openzeppelin-contracts/blob/master/contracts/token/ERC20/ERC20.sol";

contract FeroToken is ERC20{
    address public admin; //definisco un amministratore
    constructor() ERC20("FeroToken","FTN"){
        _mint(msg.sender, 10000 * 10 ** 18);
        admin = msg.sender;
    }

}
