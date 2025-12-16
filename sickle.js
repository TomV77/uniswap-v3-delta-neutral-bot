const { Web3 } = require('web3');

// Connect to Base mainnet (replace with your own Infura/Alchemy key if desired)
const web3 = new Web3('https://base-mainnet.infura.io/v3/c0660434a7f448b0a99f1b5d049e95e6');

// Your personal Sickle contract address on Base
const sickleAddress = '0xa1B402db32CCAEEF1E18A52eE1F50aeaa5535d9B';

// Uniswap V3 NonfungiblePositionManager on Base
const POSITIONS_MANAGER = '0x03a520b32C04BF3bEEf7BEb72E919cf822Ed34f1';

// Your position Token ID from VFAT.io
const TOKEN_ID = 4292587;

// ABI for NonfungiblePositionManager – includes balanceOf (for confirmation) and positions() (full details)
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

// Test connection and fetch everything
(async () => {
    try {
        // 1. Confirm connection
        const blockNumber = await web3.eth.getBlockNumber();
        console.log('Current Block Number:', blockNumber.toString());
        console.log('');

        // 2. Confirm how many positions your Sickle owns
        const balance = await positionsContract.methods.balanceOf(sickleAddress).call();
        console.log(`Your Sickle (${sickleAddress}) owns ${balance} Uniswap V3 position(s)`);
        console.log('');

        // 3. Fetch full details for your known position
        console.log(`Fetching details for Token ID #${TOKEN_ID}...`);
        const pos = await positionsContract.methods.positions(TOKEN_ID).call();

        // Human-readable output
        console.log('=== Position Details ===');
        console.log('Token0 (usually lower address, e.g., WETH):', pos.token0);
        console.log('Token1 (usually higher address, e.g., USDC):', pos.token1);
        console.log('Fee Tier:', (pos.fee / 10000).toFixed(2) + '%'); // e.g., 3000 → 0.30%
        console.log('Tick Lower:', pos.tickLower);
        console.log('Tick Upper:', pos.tickUpper);
        console.log('Liquidity:', pos.liquidity.toString());
        console.log('Uncollected Fees (Token0):', web3.utils.fromWei(pos.tokensOwed0, 'ether')); // Adjust units if needed
        console.log('Uncollected Fees (Token1):', pos.tokensOwed1.toString()); // USDC is 6 decimals usually
        console.log('');

        console.log('Success! Your delta-neutral position data is above.');
        console.log('You can now build monitoring, fee harvesting alerts, or rebalancing logic on top of this.');

    } catch (error) {
        console.error('Error:', error.message || error);
    }
})();
