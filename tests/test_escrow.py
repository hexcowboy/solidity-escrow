import pytest
import brownie
from brownie import Escrow


state = {"DEFAULT": 0, "ALLOWED": 1, "COMPLETE": 2}
visibility = {"PUBLIC": 1, "PRIVATE": 0}


@pytest.fixture
def owner(accounts):
    return accounts[0]


@pytest.fixture
def receiver(accounts):
    return accounts[9]


@pytest.fixture
def contract(owner):
    return owner.deploy(Escrow, owner, True, 0)


def test_constructor(owner, Escrow):
    contract = owner.deploy(Escrow, owner, True, 9001)
    assert contract.owner() == owner.address
    assert contract.visibility() == visibility["PUBLIC"]
    assert contract.price() == 9001


def test_visibility(owner, Escrow):
    contract = owner.deploy(Escrow, owner, False, 9001)
    assert contract.visibility() == visibility["PRIVATE"]


def test_set_escrow_price_as_owner(owner):
    contract = owner.deploy(Escrow, owner, False, 0)
    contract.setEscrowPrice(9001, {"from": owner})
    assert contract.price() == 9001


def test_set_escrow_price_as_non_owner(owner, receiver):
    contract = owner.deploy(Escrow, owner, False, 0)
    with brownie.reverts():
        contract.setEscrowPrice(9001, {"from": receiver})
    assert contract.price() != 9001


def test_whitelist_receiver(owner, receiver, contract):
    contract.whitelistReceiver(receiver, {"from": owner})
    assert contract.stateOfGivenAddress(receiver) == state["ALLOWED"]
    assert contract.stateOfGivenAddress(owner) == state["DEFAULT"]


def test_only_owner_can_whitelist(receiver, contract):
    with brownie.reverts():
        contract.whitelistReceiver(receiver, {"from": receiver})
    assert contract.stateOfGivenAddress(receiver) != state["ALLOWED"]


def test_fulfill_payment_public(owner, receiver):
    price = 9001
    contract = owner.deploy(Escrow, owner, True, price)
    transaction = contract.completePayment({"from": receiver, "amount": price})
    assert "EscrowComplete" in transaction.events
    assert transaction.events["EscrowComplete"]["amountPaid"] == price


def test_fulfill_payment_authorized(owner, receiver):
    price = 9001
    contract = owner.deploy(Escrow, owner, False, price)
    contract.whitelistReceiver(receiver, {"from": owner})
    transaction = contract.completePayment({"from": receiver, "amount": price})
    assert "EscrowComplete" in transaction.events


def test_fulfill_payment_unauthorized(owner, receiver):
    price = 9001
    contract = owner.deploy(Escrow, owner, False, price)
    with brownie.reverts():
        transaction = contract.completePayment({"from": receiver, "amount": price})
        assert "EscrowComplete" not in transaction.events


def test_force_fulfill_escrow(owner, receiver, contract):
    transaction = contract.forceCompletionForAddress(receiver.address, {"from": owner})
    assert "EscrowComplete" in transaction.events


def test_force_fulfill_escrow_as_non_owner(receiver, contract):
    with brownie.reverts():
        transaction = contract.forceCompletionForAddress(
            receiver.address, {"from": receiver}
        )
        assert "EscrowComplete" not in transaction.events


def test_withdraw_all_funds(owner, receiver, contract):
    owner_initial_balance = owner.balance()
    contract.completePayment({"from": receiver, "amount": 9001})
    assert contract.balance() == 9001
    contract.withdrawAllFunds(owner.address, {"from": owner})
    assert contract.balance() == 0
    assert owner_initial_balance + 9001 == owner.balance()
