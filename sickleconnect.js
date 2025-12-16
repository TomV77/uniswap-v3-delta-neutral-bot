const Web3 = require('web3');
const web3 = new Web3(new Web3.providers.HttpProvider('https://base-mainnet.infura.io/v3/c0660434a7f448b0a99f1b5d049e95e6'));

async function testConnection() {
    try {
        const blockNumber = await web3.eth.getBlockNumber();
        console.log('Current Block Number:', blockNumber);
    } catch (error) {
        console.error('Error connecting to Web3:', error);
    }
}

testConnection();
