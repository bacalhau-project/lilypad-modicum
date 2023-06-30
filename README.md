## MODICUM demo

Tested on Ubuntu 22.04 & 23.04

Have docker, ngrok, python, ssh, bacalhau and node.js >= v16 installed:

ngrok:

```
curl -s https://ngrok-agent.s3.amazonaws.com/ngrok.asc | sudo tee /etc/apt/trusted.gpg.d/ngrok.asc >/dev/null && echo "deb https://ngrok-agent.s3.amazonaws.com buster main" | sudo tee /etc/apt/sources.list.d/ngrok.list && sudo apt update && sudo apt install -y ngrok
```

docker:

```
sudo apt install -y docker.io
```

python:

```
sudo apt install -y curl python3-pip python3-virtualenv python3-dev libssl-dev libcurl4-openssl-dev
```

node:

```
cd ~
curl -sL https://deb.nodesource.com/setup_16.x -o /tmp/nodesource_setup.sh
sudo bash /tmp/nodesource_setup.sh
sudo apt install -y nodejs
```

ssh:

```
sudo apt install -y ssh
```

bacalhau:

```
curl -sL https://get.bacalhau.org/install.sh | bash
```

### setup block explorer

Login to https://app.tryethernal.com/settings?tab=workspace go to settings and click "RESET WORKSPACE" at the bottom.

Open a new terminal window:

```bash
ngrok http 10000
```

Copy the https url from ngrok and paste it as the RPC Server field in ethereal (in settings) then click "Update".

Then in another terminal we run the hardhat node:

```bash
git clone git@github.com:bacalhau-project/MODICUM.git
cd MODICUM
```

```
cd src/js
npm install --force
export ETHERNAL_EMAIL=kaiyadavenport@gmail.com
export ETHERNAL_PASSWORD=XXX
npx hardhat node --port 10000
```

NOTE: you might be able to grab the `ETHERNAL_PASSWORD` value from the `src/python/.env` file (read below)

Visit https://app.tryethernal.com/blocks in the browser.

IMPORTANT: each time you restart the demo - click "RESET WORKSPACE" at the bottom of the settings page on ethereal.

### various system tasks

Then create a virtualenv:

```bash
cd src/python/
python3 -m virtualenv venv
. venv/bin/activate
pip3 install -e .
```

### fill in .env file

We'll copy the .env file sample and then fill in the details for your one. Note the .env file is in .gitignore because it will contain private keys...
```
cp src/python/.env.sample src/python/.env
```

Then we create a new ssh keypair:

```bash
ssh-keygen -f ~/.ssh/modicum-demo
```
Hit enter three times to use the defaults

Now we adjust the values on the `src/python/.env` file paying note to the following:

 * `DIR` = `/home/YOURUSERNAME` (pointing to the parent directory of where you checked out MODICUM)
 * `pubkey` = the public key we just generated
 * `sshkey` = the path to the private key we just generated

If you are deploying to a real blockchain and have your private key, also fill in the `PRIVATE_KEY_0` (and optionally, `RPC_TOKEN` to send a Bearer token to the RPC endpoint if your provider requires it)

### influx DB

Then we setup influxDB - in another pane (install docker and `sudo adduser $USER docker` and log out and log in again):

```bash
docker run -d \
  --name influx \
  -p 8086:8086 \
  influxdb:1.8.10
```

Now we need to setup the database:

```bash
docker exec -ti influx influx
```
```
create database collectd;
```
```
show databases;
```
```
exit
```

### env and virtualenv files

From now on, activate the virtual env and source the environment variables in any new panes where you run a python process, like this:

```bash
cd src/python
. ./venv/bin/activate
source .env
```

### compile contracts

Then we source the file and compile the contracts:

```bash
cd src/python/
source .env
echo $CONTRACTSRC
docker run -it --rm\
		--name solcTest \
		--mount type=bind,source="${CONTRACTSRC}",target=/solidity/input \
		--mount type=bind,source="${CONTRACTSRC}/output",target=/solidity/output \
		ethereum/solc:0.4.25 \
		--overwrite --bin --bin-runtime --ast --abi --asm -o /solidity/output /solidity/input/Modicum.sol
```

Ignore the warnings.

### update paths

You need to change all instances of `/home/luke/pb` in the `0_experiments/demo` directory to your own username and path to parent directory of MODICUM.

### run services

Now we start the various processes (each in it's own pane):

* IMPORTANT: don't forget to activate the virtualenv in each pane! `. venv/bin/activate` inside `src/python`
* IMPORTANT: run these in this exact order!

```bash
modicum runAsCM
```

```bash
modicum runAsSolver
```

```bash
sudo -E $(which modicum) runAsDir
```
(sudo because it will do a bunch of stuff like creating users :-O)

```bash
modicum runAsMediator
```

NOTE: replace this path with the absolute path on your system

```bash
modicum startRP --path $(realpath $PWD/../..)/0_experiments/demo/ --index 1
```

edit `0_experiments/demo/player0` to update the paths

```bash
modicum startJC --playerpath $(realpath $PWD/../..)/0_experiments/demo/ --index 0
```

Keep an eye out on the `startRP` pane - the bacalhau job ID will get printed there with a link to it on the dashboard.
