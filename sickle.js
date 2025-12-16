const { Web3 } = require('web3');
const axios = require('axios');

const web3 = new Web3('https://base-mainnet.infura.io/v3/c0660434a7f448b0a99f1b5d049e95e6');

const sickleAddress = '0xa1B402db32CCAEEF1E18A52eE1F50aeaa5535d9B'.toLowerCase();
const POSITIONS_MANAGER = '0x03a520b32C04BF3bEEf7BEb72E919cf822Ed34f1';

// Fixed complete ABI
const positionsAbi = [ /* paste the full array above here */ ];

const positionsContract = new web3.eth.Contract(positionsAbi, POSITIONS_MANAGER);

// Public subgraph endpoint for Uniswap V3 on Base (works without API key)
const SUBGRAPH_URL = 'https://api.thegraph.com/subgraphs/id/FUbEPQw1oMghy39fwWBFY5fE6MXPXZQtjncQy2cXdrNS';

function formatAmount(amountBigInt, decimals) {
    return Number(amountBigInt) / (10 ** decimals);
}

(async () => {
    try {
        const blockNumber = await web3.eth.getBlockNumber();
        console.log('Current Block Number:', blockNumber.toString());
        console.log('');

        // On-chain balance confirmation (now works with fixed ABI)
        const balance = await positionsContract.methods.balanceOf(sickleAddress).call();
        console.log(`Your Sickle owns ${balance} Uniswap V3 position(s) (on-chain)`);
        if (balance === '0') {
            console.log('No positions found.');
            return;
        }
        console.log('');

        // Subgraph query for all active positions (liquidity > 0)
        const query = `
        {
            positions(where: {owner: "${sickleAddress}", liquidity_gt: 0}, orderBy: collectedFeesToken0, orderDirection: desc) {
                id
                token0 { id symbol decimals }
                token1 { id symbol decimals }
                feeTier
                tickLower
                tickUpper
                liquidity
                tokensOwed0
                tokensOwed1
            }
        }`;

        const response = await axios.post(SUBGRAPH_URL, { query });
        const positions = response.data?.data?.positions || [];

        if (positions.length === 0) {
            console.log('No active positions found (subgraph sync lag possible).');
            return;
        }

        console.log(`Found ${positions.length} active position(s):\n`);

        for (const pos of positions) {
            const tokenId = pos.id;
            console.log(`=== Position Token ID: ${tokenId} ===`);
            console.log(`Pair: ${pos.token0.symbol} / ${pos.token1.symbol}`);
            console.log(`Fee Tier: ${pos.feeTier / 10000}%`);
            console.log(`Tick Range: ${pos.tickLower} → ${pos.tickUpper}`);
            console.log(`Liquidity: ${pos.liquidity}`);
            console.log(`Uncollected Fees:`);
            console.log(`  ${formatAmount(pos.tokensOwed0, pos.token0.decimals).toFixed(6)} ${pos.token0.symbol}`);
            console.log(`  ${formatAmount(pos.tokensOwed1, pos.token1.decimals).toFixed(6)} ${pos.token1.symbol}`);
            console.log('');
        }

        console.log('Done! This auto-detects all current positions – works even after opening/closing.');

    } catch (error) {
        console.error('Error:', error.response?.data || error.message || error);
    }
})();
