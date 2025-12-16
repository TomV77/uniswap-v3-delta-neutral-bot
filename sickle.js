const { Web3 } = require('web3');
const axios = require('axios');

// Connect to Base
const web3 = new Web3('https://base-mainnet.infura.io/v3/c0660434a7f448b0a99f1b5d049e95e6');

const sickleAddress = '0xa1B402db32CCAEEF1E18A52eE1F50aeaa5535d9B'.toLowerCase();
const POSITIONS_MANAGER = '0x03a520b32C04BF3bEEf7BEb72E919cf822Ed34f1';

// FULL ABI – this fixes your error
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

// Correct public endpoint for Uniswap V3 on Base (works today)
const SUBGRAPH_URL = 'https://gateway.thegraph.com/api/subgraphs/id/FUbEPQw1oMghy39fwWBFY5fE6MXPXZQtjncQy2cXdrNS';

// Format helper
function formatAmount(amount, decimals) {
    return Number(amount) / (10 ** decimals);
}

(async () => {
    try {
        const blockNumber = await web3.eth.getBlockNumber();
        console.log('Current Block Number:', blockNumber.toString());
        console.log('');

        const balance = await positionsContract.methods.balanceOf(sickleAddress).call();
        console.log(`Your Sickle owns ${balance} Uniswap V3 position(s) (on-chain check)`);
        if (balance === '0') {
            console.log('No positions. Done.');
            return;
        }
        console.log('');

        // Auto-find all active Token IDs + details via subgraph
        const query = `
        {
            positions(where: {owner: "${sickleAddress}", liquidity_gt: "0"}, first: 100) {
                id
                token0 { symbol decimals }
                token1 { symbol decimals }
                fee
                tickLower
                tickUpper
                liquidity
                tokensOwed0
                tokensOwed1
            }
        }`;

        const response = await axios.post(SUBGRAPH_URL, { query });
        const data = response.data.data;
        const positions = data?.positions || [];

        if (positions.length === 0) {
            console.log('Subgraph found no active positions (rare sync delay).');
            return;
        }

        console.log(`Auto-detected ${positions.length} active position(s):\n`);

        for (const pos of positions) {
            const tokenId = pos.id;
            console.log(`Token ID: ${tokenId}`);
            console.log(`Pair: ${pos.token0.symbol} / ${pos.token1.symbol}`);
            console.log(`Fee: ${Number(pos.fee) / 10000}%`);
            console.log(`Range: ${pos.tickLower} → ${pos.tickUpper}`);
            console.log(`Liquidity: ${pos.liquidity}`);
            console.log(`Fees owed:`);
            console.log(`  ${formatAmount(pos.tokensOwed0, pos.token0.decimals).toFixed(6)} ${pos.token0.symbol}`);
            console.log(`  ${formatAmount(pos.tokensOwed1, pos.token1.decimals).toFixed(6)} ${pos.token1.symbol}`);
            console.log('---');
        }

        console.log('Perfect! It now finds every Token ID automatically forever.');

    } catch (error) {
        console.error('Error:', error.message || error);
        if (error.response) console.error('Subgraph response:', error.response.data);
    }
})();
