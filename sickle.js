const { Web3 } = require('web3');
const web3 = new Web3('https://base-mainnet.infura.io/v3/c0660434a7f448b0a99f1b5d049e95e6');

// Test connection
(async () => {
    try {
        const blockNumber = await web3.eth.getBlockNumber();
        console.log('Current Block Number:', blockNumber);
    } catch (error) {
        console.error('Error connecting:', error);
    }
})();

// Your personal Sickle address on Base
const sickleAddress = '0xa1B402db32CCAEEF1E18A52eE1F50aeaa5535d9B';

// Uniswap V3 Positions NFT manager on Base
const UNISWAP_V3_NFT_ADDRESS_BASE = '0x03a520b32C04BF3bEEf7BEb72E919cf822Ed34f1';

// Minimal ABI for NonfungiblePositionManager (only what we need: balanceOf and tokenOfOwnerByIndex)
const positionsAbi = [
    {"inputs":[{"internalType":"address","name":"owner","type":"address"}],"name":"balanceOf","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},
    {"inputs":[{"internalType":"uint256","name":"index","type":"uint256"}],"name":"tokenOfOwnerByIndex","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"}
];

const positionsContract = new web3.eth.Contract(positionsAbi, UNISWAP_V3_NFT_ADDRESS_BASE);

// Function to fetch all Uniswap V3 position token IDs owned by your Sickle
async function fetchPositionTokenIds(sickleAddr) {
    try {
        const balance = await positionsContract.methods.balanceOf(sickleAddr).call();
        console.log(`Your Sickle owns ${balance} Uniswap V3 position(s)`);

        const tokenIds = [];
        for (let i = 0; i < balance; i++) {
            const tokenId = await positionsContract.methods.tokenOfOwnerByIndex(sickleAddr, i).call();
            tokenIds.push(tokenId);
            console.log(`Position Token ID #${i}: ${tokenId}`);
        }
        return tokenIds;
    } catch (error) {
        console.error('Error fetching positions:', error);
        throw error;
    }
}

// Test it
(async () => {
    try {
        const tokenIds = await fetchPositionTokenIds(sickleAddress);
        console.log('All position token IDs:', tokenIds);
    } catch (error) {
        console.error('Failed:', error);
    }
})();
