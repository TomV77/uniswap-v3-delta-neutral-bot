const { Web3 } = require('web3');
require('dotenv').config();

// Configuration from environment or defaults
const RPC_URL = process.env.RPC_URL || 'https://base-mainnet.infura.io/v3/YOUR_INFURA_PROJECT_ID';
const sickleAddress = process.env.VFAT_SICKLE_ADDRESS || '0xa1B402db32CCAEEF1E18A52eE1F50aeaa5535d9B';
const POSITIONS_MANAGER = process.env.UNISWAP_V3_NFT_ADDRESS || '0x03a520b32C04BF3bEEf7BEb72E919cf822Ed34f1';
const TOKEN_ID = parseInt(process.env.TEST_TOKEN_ID || '4294280');

// Warn if using default RPC URL
if (RPC_URL.includes('YOUR_INFURA_PROJECT_ID')) {
    console.warn('⚠ Using default RPC URL - set RPC_URL in .env file for actual testing');
}

// Connect to Base mainnet
const web3 = new Web3(RPC_URL);

// ABI with balanceOf and positions()
const positionsAbi = [
    {
        "inputs": [{"internalType": "address", "name": "owner", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [{"internalType": "uint256", "name": "tokenId", "type": "uint256"}],
        "name": "positions",
        "outputs": [
            {"internalType": "uint96", "name": "nonce", "type": "uint96"},
            {"internalType": "address", "name": "operator", "type": "address"},
            {"internalType": "address", "name": "token0", "type": "address"},
            {"internalType": "address", "name": "token1", "type": "address"},
            {"internalType": "uint24", "name": "fee", "type": "uint24"},
            {"internalType": "int24", "name": "tickLower", "type": "int24"},
            {"internalType": "int24", "name": "tickUpper", "type": "int24"},
            {"internalType": "uint128", "name": "liquidity", "type": "uint128"},
            {"internalType": "uint256", "name": "feeGrowthInside0LastX128", "type": "uint256"},
            {"internalType": "uint256", "name": "feeGrowthInside1LastX128", "type": "uint256"},
            {"internalType": "uint128", "name": "tokensOwed0", "type": "uint128"},
            {"internalType": "uint128", "name": "tokensOwed1", "type": "uint128"}
        ],
        "stateMutability": "view",
        "type": "function"
    }
];

const positionsContract = new web3.eth.Contract(positionsAbi, POSITIONS_MANAGER);

// Helper to format amounts
function formatAmount(amountBigInt, decimals) {
    return Number(amountBigInt) / (10 ** decimals);
}

(async () => {
    try {
        // Confirm connection and block
        const blockNumber = await web3.eth.getBlockNumber();
        console.log('Current Block Number:', blockNumber.toString());
        console.log('');

        // Confirm position count
        const balance = await positionsContract.methods.balanceOf(sickleAddress).call();
        console.log(`Your Sickle (${sickleAddress}) owns ${balance} Uniswap V3 position(s)`);
        console.log('');

        // Fetch position details
        console.log(`Fetching details for Token ID #${TOKEN_ID}...`);
        const pos = await positionsContract.methods.positions(TOKEN_ID).call();

        // Human-readable output
        console.log('=== Position Details ===');
        console.log('Token0: WETH @', pos.token0);
        console.log('Token1: USDC @', pos.token1);
        console.log('Fee Tier:', Number(pos.fee) / 10000 + '%');  // Fixed BigInt division
        console.log('Tick Lower:', pos.tickLower.toString());
        console.log('Tick Upper:', pos.tickUpper.toString());
        console.log('Liquidity:', pos.liquidity.toString());
        console.log('Uncollected Fees (WETH):', formatAmount(pos.tokensOwed0, 18).toFixed(6));
        console.log('Uncollected Fees (USDC):', formatAmount(pos.tokensOwed1, 6).toFixed(2));
        console.log('');

        console.log('Success! This matches your VFAT.io CL-60 WETH/USDC 0.3% position.');
        console.log('You can now monitor fees, check in-range status, or build harvesting logic.');

    } catch (error) {
        console.error('Error:', error.message || error);
    }
})();
