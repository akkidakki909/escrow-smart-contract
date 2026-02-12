// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

contract PeerEscrowWithDispute {

    struct Escrow {
        address payable sender;
        address payable receiver;
        uint amount;
        uint deadline;
        bool released;
        bool refunded;
        bool disputed;
    }

    uint public escrowCount;
    address public arbiter;

    mapping(uint => Escrow) public escrows;

    event EscrowCreated(uint escrowId, address sender, address receiver, uint amount);
    event PaymentReleased(uint escrowId);
    event Refunded(uint escrowId);
    event DisputeRaised(uint escrowId);
    event DisputeResolved(uint escrowId, address winner);

    constructor(address _arbiter) {
        arbiter = _arbiter;
    }

    // Create escrow and deposit funds
    function createEscrow(address payable _receiver, uint _durationInMinutes) public payable {
        require(msg.value > 0, "Send ETH");
        require(_receiver != msg.sender, "Cannot pay yourself");

        escrowCount++;

        escrows[escrowCount] = Escrow({
            sender: payable(msg.sender),
            receiver: _receiver,
            amount: msg.value,
            deadline: block.timestamp + (_durationInMinutes * 1 minutes),
            released: false,
            refunded: false,
            disputed: false
        });

        emit EscrowCreated(escrowCount, msg.sender, _receiver, msg.value);
    }

    // Sender confirms delivery
    function confirmDelivery(uint _escrowId) public {
        Escrow storage escrow = escrows[_escrowId];

        require(msg.sender == escrow.sender, "Only sender");
        require(!escrow.disputed, "Dispute active");
        require(!escrow.released && !escrow.refunded, "Already settled");

        escrow.released = true;
        escrow.receiver.transfer(escrow.amount);

        emit PaymentReleased(_escrowId);
    }

    // Refund before release
    function refund(uint _escrowId) public {
        Escrow storage escrow = escrows[_escrowId];

        require(msg.sender == escrow.sender, "Only sender");
        require(!escrow.disputed, "Dispute active");
        require(!escrow.released && !escrow.refunded, "Already settled");

        escrow.refunded = true;
        escrow.sender.transfer(escrow.amount);

        emit Refunded(_escrowId);
    }

    // Raise dispute (either party)
    function raiseDispute(uint _escrowId) public {
        Escrow storage escrow = escrows[_escrowId];

        require(msg.sender == escrow.sender || msg.sender == escrow.receiver, "Not participant");
        require(!escrow.released && !escrow.refunded, "Already settled");

        escrow.disputed = true;

        emit DisputeRaised(_escrowId);
    }

    // Arbiter resolves dispute
    function resolveDispute(uint _escrowId, bool releaseToReceiver) public {
        require(msg.sender == arbiter, "Only arbiter");

        Escrow storage escrow = escrows[_escrowId];

        require(escrow.disputed, "No dispute");
        require(!escrow.released && !escrow.refunded, "Already settled");

        if (releaseToReceiver) {
            escrow.released = true;
            escrow.receiver.transfer(escrow.amount);
            emit DisputeResolved(_escrowId, escrow.receiver);
        } else {
            escrow.refunded = true;
            escrow.sender.transfer(escrow.amount);
            emit DisputeResolved(_escrowId, escrow.sender);
        }
    }

    // Auto release after deadline (if no dispute)
    function autoRelease(uint _escrowId) public {
        Escrow storage escrow = escrows[_escrowId];

        require(block.timestamp >= escrow.deadline, "Deadline not reached");
        require(!escrow.disputed, "Dispute active");
        require(!escrow.released && !escrow.refunded, "Already settled");

        escrow.released = true;
        escrow.receiver.transfer(escrow.amount);

        emit PaymentReleased(_escrowId);
    }
}
