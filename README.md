# escrow-smart-contract
# Escrow-Based Peer Payments 

A decentralized escrow smart contract built using Solidity to eliminate fraud in peer-to-peer payments.

##  Problem Statement

In peer-to-peer payments (especially on campuses), users send money for:

- Second-hand books
- Notes
- Freelance work
- Small services

There is **no trust guarantee**.

- Sender may not receive service.
- Receiver may not get paid after completing work.
- UPI offers no escrow protection.
- Chargebacks and fraud are common.
- 
##  Solution

A blockchain-based escrow smart contract that:

1. Locks funds when sender deposits.
2. Releases payment only after confirmation.
3. Automatically releases after deadline.
4. Supports dispute resolution via neutral arbiter.

This replaces traditional UPI trust with **trustless smart contract logic**.

##  Features

-  Funds locked inside smart contract
- Deadline-based auto release
- Dispute raising by either party
-  Arbiter-based resolution
-  No admin control over funds
-  Transparent on-chain logic



##  Smart Contract Architecture

Flow:

Deposit → Task Completion → 
(Confirm OR AutoRelease OR Dispute)

If Dispute:
Arbiter decides winner → Funds transferred accordingly.

---

##  Contract Functions

### createEscrow(address receiver, uint duration)
Sender deposits ETH and sets deadline.

### confirmDelivery(uint escrowId)
Sender releases payment to receiver.

### refund(uint escrowId)
Sender cancels before release.

### raiseDispute(uint escrowId)
Either party can raise dispute.

### resolveDispute(uint escrowId, bool releaseToReceiver)
Arbiter resolves dispute.

### autoRelease(uint escrowId)
Automatically releases funds after deadline.

---

## Tech Stack

- Solidity ^0.8.19
- Hardhat
- Ethereum (EVM Compatible)


##  How To Run Locally

### 1. Install Dependencies
npm install

### 2. Compile Contract
npx hardhat compile

### 3. Run Local Node
npx hardhat node

### 4. Deploy Contract
npx hardhat run scripts/deploy.js --network localhost

---

##  Testing via Remix

1. Go to https://remix.ethereum.org
2. Paste contract in new file.
3. Compile with Solidity 0.8.19
4. Deploy using JavaScript VM.
5. Test escrow lifecycle.

##  Real-World Use Cases

- Campus freelancing
- Digital marketplace
- Peer tutoring payments
- Small business services
- Online second-hand marketplaces

##  Future Improvements

- DAO-based arbitration
- Multi-signature dispute resolution
- ERC20 token support
- Reputation system
- Frontend DApp (React + MetaMask)
- Deployment on Polygon

---

##  Authors

Akshat Tripathi 
Ameya Morgaonkar
Arnav Jakate
Ayush Andure


