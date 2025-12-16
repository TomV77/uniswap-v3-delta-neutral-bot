const { Web3 } = require('web3');
const web3 = new Web3('https://base-mainnet.infura.io/v3/c0660434a7f448b0a99f1b5d049e95e6');

// Test connection
(async () => {
    try {
        const blockNumber = await web3.eth.getBlockNumber();
        console.log('Current Block Number:', blockNumber);
    } catch (error) {
        console.error('Connection error:', error);
    }
})();

// Your Sickle address
const sickleAddress = '0xa1B402db32CCAEEF1E18A52eE1F50aeaa5535d9B';

// Correct Base Uniswap V3 Positions Manager
const POSITIONS_MANAGER = '0x03a520b32C04BF3bEEf7BEb72E919cf822Ed34f1';

// Extended ABI to include the positions() function for details later
const positionsAbi = [
    {"inputs":[{"internalType":"address","name":"owner","type":"address"}],"name":"balanceOf","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},
    {"inputs":[{"internalType":"uint256","name":"index","type":"uint256"}],"name":"tokenOfOwnerByIndex","outputs":[{"internalType":"uint256","name":"tokenId","type":"uint256"}],"stateMutability":"view","type":"function"},
    // Add this for position details once you have tokenIds
    {"inputs":[{"internalType":"uint256","name":"tokenId","type":"uint256"}],"name":"positions","outputs":[ /* full struct here if needed */ ],"stateMutability":"view","type":"function"}
];

const positionsContract = new web3.eth.Contract(positionsAbi, POSITIONS_MANAGER);

async function fetchPositionTokenIds(sickleAddr) {
    try {
        const balance = await positionsContract.methods.balanceOf(sickleAddr).call();
        console.log(`Your Sickle owns ${balance} Uniswap V3 position(s)`);

        if (balance === '0') {
            console.log('No positions found.');
            return [];
        }

        // This loop will likely fail due to revert — catch it
        const tokenIds = [];
        for (let i = 0; i < parseInt(balance); i++) {
            try {
                const tokenId = await positionsContract.methods.tokenOfOwnerByIndex(sickleAddr, i).call();
                tokenIds.push(tokenId);
                console.log(`Position Token ID #${i}: ${tokenId}`);
            } catch (err) {
                console.error(`Failed to fetch index ${i}:`, err.message);
            }
        }
        return tokenIds;
    } catch (error) {
        console.error('balanceOf reverted (common with contract owners like Sickle):', error.message);
        console.log('\nManual lookup required:');
        console.log(`Visit https://basescan.org/address/${sickleAddr}#tokentxns-nft`);
        console.log('Filter for UNI-V3-POS transfers to see your position token IDs.');
        console.log('Alternatively, check your positions on https://app.uniswap.org or vfat.io dashboard.');
        return [];
    }
}

// Run it
(async () => {
    try {
        await fetchPositionTokenIds(sickleAddress);
    } catch (error) {
        console.error('Unexpected error:', error);
    }
})();
