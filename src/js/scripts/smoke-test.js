const hre = require('hardhat')

const {
  getWallet,
} = require('../accounts')

const {
  ethers,
  deployments,
} = hre

const {
  transfer,
} = require('../utils')

async function main() {
  const deployment = await deployments.get('NaiveExamplesClient')
  const NaiveExamplesClient = await ethers.getContractFactory("NaiveExamplesClient")
  const examplesContract = NaiveExamplesClient.attach(deployment.address)
  const wallet = getWallet('job_creator')
  const signer = wallet.connect(hre.ethers.provider)
  const trx = await examplesContract
    .connect(signer)
    .runCowsay("holy cow", {
      value: ethers.utils.parseEther("1"),
      gasPrice: 1,
      gasLimit: ethers.BigNumber.from('10000000'),
    })

  const receipt = await trx.wait()
  console.log(`trx: ${JSON.stringify(trx)}`)
  console.log(`receipt: ${JSON.stringify(receipt)}`)
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});