const { Web3 } = require('web3');
const web3 = new Web3('https://base-mainnet.infura.io/v3/c0660434a7f448b0a99f1b5d049e95e6');

// Test the connection
(async () => {
    try {
        const blockNumber = await web3.eth.getBlockNumber();
        console.log('Current Block Number:', blockNumber);
    } catch (error) {
        console.error('Error connecting to the Web3 provider:', error);
    }
})();

// Sickle contract ABI (provided by you)
const sickleAbi = [
    {"inputs":[{"internalType":"address","name":"sickleRegistry_","type":"address"}],"stateMutability":"nonpayable","type":"constructor"},
    {"inputs":[{"internalType":"address","name":"caller","type":"address"}],"name":"CallerNotWhitelisted","type":"error"},
    {"inputs":[],"name":"MulticallParamsMismatchError","type":"error"},
    {"inputs":[],"name":"NotOwnerError","type":"error"},
    {"inputs":[],"name":"NotStrategyError","type":"error"},
    {"inputs":[{"internalType":"address","name":"target","type":"address"}],"name":"TargetNotWhitelisted","type":"error"},
    {"anonymous":false,"inputs":[{"indexed":false,"internalType":"uint8","name":"version","type":"uint8"}],"name":"Initialized","type":"event"},
    {"inputs":[],"name":"approved","outputs":[{"internalType":"address","name":"","type":"address"}],"stateMutability":"view","type":"function"},
    {"inputs":[{"internalType":"address","name":"sickleOwner_","type":"address"},{"internalType":"address","name":"approved_","type":"address"}],"name":"initialize","outputs":[],"stateMutability":"nonpayable"},
    {"inputs":[{"internalType":"address","name":"caller","type":"address"}],"name":"isOwnerOrApproved","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"view"},
    {"inputs":[{"internalType":"address[]","name":"targets","type":"address[]"},{"internalType":"bytes[]","name":"data","type":"bytes[]"}],"name":"multicall","outputs":[],"stateMutability":"payable"},
    {"inputs":[{"internalType":"address","name":"","type":"address"},{"internalType":"address","name":"","type":"address"},{"internalType":"uint256[]","name":"","type":"uint256[]"},{"internalType":"uint256[]","name":"","type":"uint256[]"},{"internalType":"bytes","name":"","type":"bytes"}],"name":"onERC1155BatchReceived","outputs":[{"internalType":"bytes4","name":"","type":"bytes4"}],"stateMutability":"pure"},
    {"inputs":[{"internalType":"address","name":"","type":"address"},{"internalType":"address","name":"","type":"address"},{"internalType":"uint256","name":"","type":"uint256"},{"internalType":"uint256","name":"","type":"uint256"},{"internalType":"bytes","name":"","type":"bytes"}],"name":"onERC1155Received","outputs":[{"internalType":"bytes4","name":"","type":"bytes4"}],"stateMutability":"pure"},
    {"inputs":[{"internalType":"address","name":"","type":"address"},{"internalType":"address","name":"","type":"address"},{"internalType":"uint256","name":"","type":"uint256"},{"internalType":"bytes","name":"","type":"bytes"}],"name":"onERC721Received","outputs":[{"internalType":"bytes4","name":"","type":"bytes4"}],"stateMutability":"pure"},
    {"inputs":[],"name":"owner","outputs":[{"internalType":"address","name":"","type":"address"}],"stateMutability":"view"},
    {"inputs":[],"name":"registry","outputs":[{"internalType":"contract SickleRegistry","name":"","type":"address"}],"stateMutability":"view"},
    {"inputs":[{"internalType":"address","name":"newApproved","type":"address"}],"name":"setApproved","outputs":[],"stateMutability":"nonpayable"},
    {"stateMutability":"payable","type":"receive"}
];

// Sickle contract address
const sickleAddress = '0xba4b2d23ccafeef18a52e1f50eaaa535d9b';

// Initialize the contract
const sickleContract = new web3.eth.Contract(sickleAbi, sickleAddress);

// Function to fetch the registry contract address
async function getRegistryAddress() {
    try {
        const registryAddress = await sickleContract.methods.registry().call();
        console.log('Registry Address:', registryAddress);
        return registryAddress;
    } catch (error) {
        console.error('Error fetching registry address:', error);
        throw error;
    }
}

// Example function to fetch position information
async function fetchPosition(address) {
    try {
        const registryAddress = await getRegistryAddress();
        console.log(`Using registry contract at: ${registryAddress}`);

        // Add the SickleRegistry ABI here
        const registryAbi = [ /* Add SickleRegistry ABI when available */ ];
        const registryContract = new web3.eth.Contract(registryAbi, registryAddress);

        // Assuming position-related function exists in Registry (e.g., balanceOf)
        const balance = await registryContract.methods.balanceOf(address).call();
        console.log(`Balance for ${address}: ${balance}`);
        return balance;
    } catch (error) {
        console.error('Error fetching position:', error);
        throw error;
    }
}

// Test the workflow
(async () => {
    const walletAddress = '0xYourWalletAddressHere';
    try {
        const position = await fetchPosition(walletAddress);
        console.log('Position fetched successfully:', position);
    } catch (error) {
        console.error('Failed to fetch position:', error);
    }
})();
