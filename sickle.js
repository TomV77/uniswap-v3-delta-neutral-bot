const { Web3 } = require('web3');
const axios = require('axios');

const web3 = new Web3('https://base-mainnet.infura.io/v3/c0660434a7f448b0a99f1b5d049e95e6');

const sickleAddress = '0xa1B402db32CCAEEF1E18A52eE1F50aeaa5535d9B'.toLowerCase(); // lowercase for subgraph
const POSITIONS_MANAGER = '0x03a520b32C04BF3bEEf7BEb72E919cf822Ed34f1';

const positionsAbi = [ /* same as before: balanceOf and positions() */ 
    { /* balanceOf */ },
    { /* positions(uint256) full struct */ }
    // Paste the two ABI entries from previous script
];

const positionsContract = new web3.eth.Contract(positionsAbi, POSITIONS_MANAGER);

const SUBGRAPH_URL = 'https://api.thegraph.com/subgraphs/name/uniswap/uniswap-v3-base';

// Helper for amounts
function formatAmount(amountBigInt, decimals) {
    return Number(amountBigInt) / (10 ** decimals);
}

(async () => {
    try {
        const blockNumber = await web3.eth.getBlockNumber();
        console.log('Current Block Number:', blockNumber.toString());
        console.log('');

        const balance = await positionsContract.methods.balanceOf(sickleAddress).call();
        console.log(`Your Sickle owns ${balance} Uniswap V3 position(s)`);
        if (balance === '0') {
            console.log('No active positions.');
            return;
        }
        console.log('');

        // Query subgraph for all position IDs owned by your Sickle with liquidity > 0
        const query = `
        {
            positions(where: {owner: "${sickleAddress}", liquidity_gt: 0}, first: 100) {
                id
                liquidity
                token0 { symbol }
                token1 { symbol }
                fee
                tickLower
                tickUpper
                tokensOwed0
                tokensOwed1
            }
        }`;

        const response = await axios.post(SUBGRAPH_URL, { query });
        const positions = response.data.data.positions;

        if (positions.length === 0) {
            console.log('No active positions found via subgraph (possible sync lag).');
            return;
        }

        console.log(`Found ${positions.length} active position(s) via subgraph:\n`);

        for (const pos of positions) {
            const tokenId = pos.id;
            console.log(`=== Position Token ID: ${tokenId} ===`);
            console.log('Pair:', pos.token0.symbol, '/', pos.token1.symbol);
            console.log('Fee Tier:', Number(pos.fee) / 10000 + '%');
            console.log('Tick Range:', pos.tickLower, '→', pos.tickUpper);
            console.log('Liquidity:', pos.liquidity);
            console.log('Uncollected Fees:', 
                formatAmount(pos.tokensOwed0, pos.token0.symbol === 'WETH' ? 18 : 6),
                pos.token0.symbol,
                '+',
                formatAmount(pos.tokensOwed1, pos.token1.symbol === 'USDC' ? 6 : 18),
                pos.token1.symbol
            );
            console.log('');
        }

        console.log('Success! Positions auto-detected – no hardcoding needed.');
        console.log('This will update automatically when you open/close positions.');

    } catch (error) {
        console.error('Error:', error.message || error);
    }
})();
