import json
import struct
import time
from solana.transaction import Signature
from solana.rpc.commitment import Processed, Confirmed
from solana.rpc.types import TokenAccountOpts, TxOpts
from solana.transaction import AccountMeta
from solders.keypair import Keypair
from spl.token.instructions import (
    CloseAccountParams,
    close_account,
    get_associated_token_address,
)
from solders.instruction import Instruction
from solders.message import MessageV0
from solders.transaction import VersionedTransaction
from solana.rpc.api import Client, Keypair
from solders.compute_budget import set_compute_unit_price,set_compute_unit_limit
from PumpDotFun.utils.constants import *
from utils.coin_data import get_coin_data, tokens_for_sol
import os
from utils.utility import confirm_txn, get_token_balance,get_token_price




from dotenv import load_dotenv
# Load.env file
load_dotenv()
# config = dotenv_values(".env")
UNIT_BUDGET= os.getenv("UNIT_BUDGET")
UNIT_PRICE= os.getenv("UNIT_PRICE")
RPC_HTTPS_URL= os.getenv("RPC_URL")
client = Client(os.getenv("RPC_URL"))
payer_keypair=Keypair.from_base58_string(os.getenv("PRIVATE_KEY"))
def sell(mint_str: str, percentage: int = 100, slippage: int = 5) -> bool:
    try:
        print(f"Starting sell transaction for mint: {mint_str}")

        if not (1 <= percentage <= 100):
            print("Percentage must be between 1 and 100.")
            return False

        coin_data = get_coin_data(mint_str)

        if not coin_data:
            print("Failed to retrieve coin data.")
            return False

        if coin_data.complete:
            print("Warning: This token has bonded and is only tradable on Raydium.")
            return

        MINT = coin_data.mint
        BONDING_CURVE = coin_data.bonding_curve
        ASSOCIATED_BONDING_CURVE = coin_data.associated_bonding_curve
        USER = payer_keypair.pubkey()
        ASSOCIATED_USER = get_associated_token_address(USER, MINT)

        print("Retrieving token balance...")
        token_balance = get_token_balance(mint_str)
        if token_balance == 0 or token_balance is None:
            print("Token balance is zero. Nothing to sell.")
            return False
        print(f"Token Balance: {token_balance}")

        print("Calculating transaction amounts...")
        sol_dec = 1e9
        token_dec = 1e6
        amount = int(token_balance * token_dec)

        virtual_sol_reserves = coin_data.virtual_sol_reserves / sol_dec
        virtual_token_reserves = coin_data.virtual_token_reserves / token_dec
        sol_out = tokens_for_sol(token_balance, virtual_sol_reserves, virtual_token_reserves)

        slippage_adjustment = 1 - (slippage / 100)
        min_sol_output = int((sol_out * slippage_adjustment) * sol_dec)
        print(f"Amount: {amount}, Minimum Sol Out: {min_sol_output}")

        print("Creating swap instructions...")
        keys = [
            AccountMeta(pubkey=GLOBAL, is_signer=False, is_writable=False),
            AccountMeta(pubkey=FEE_RECIPIENT, is_signer=False, is_writable=True),
            AccountMeta(pubkey=MINT, is_signer=False, is_writable=False),
            AccountMeta(pubkey=BONDING_CURVE, is_signer=False, is_writable=True),
            AccountMeta(pubkey=ASSOCIATED_BONDING_CURVE, is_signer=False, is_writable=True),
            AccountMeta(pubkey=ASSOCIATED_USER, is_signer=False, is_writable=True),
            AccountMeta(pubkey=USER, is_signer=True, is_writable=True),
            AccountMeta(pubkey=SYSTEM_PROGRAM, is_signer=False, is_writable=False),
            AccountMeta(pubkey=ASSOC_TOKEN_ACC_PROG, is_signer=False, is_writable=False),
            AccountMeta(pubkey=TOKEN_PROGRAM, is_signer=False, is_writable=False),
            AccountMeta(pubkey=EVENT_AUTHORITY, is_signer=False, is_writable=False),
            AccountMeta(pubkey=PUMP_FUN_PROGRAM, is_signer=False, is_writable=False)
        ]

        data = bytearray()
        data.extend(bytes.fromhex("33e685a4017f83ad"))
        data.extend(struct.pack('<Q', amount))
        data.extend(struct.pack('<Q', min_sol_output))
        swap_instruction = Instruction(PUMP_FUN_PROGRAM, bytes(data), keys)

        instructions = [
            set_compute_unit_limit(int(UNIT_BUDGET)),
            set_compute_unit_price(int(UNIT_PRICE)),
            swap_instruction,
        ]

        if percentage == 100:
            print("Preparing to close token account after swap...")
            close_account_instruction = close_account(CloseAccountParams(TOKEN_PROGRAM, ASSOCIATED_USER, USER, USER))
            instructions.append(close_account_instruction)

        print("Compiling transaction message...")
        compiled_message = MessageV0.try_compile(
            payer_keypair.pubkey(),
            instructions,
            [],
            client.get_latest_blockhash().value.blockhash,
        )

        print("Sending transaction...")
        txn_sig = client.send_transaction(
            txn=VersionedTransaction(compiled_message, [payer_keypair]),
            opts=TxOpts(skip_preflight=False)
        ).value
        print(f"Transaction Signature: {txn_sig}")

        print("Confirming transaction...")
        confirmed = confirm_txn(txn_sig)

        print(f"Transaction confirmed: {confirmed}   https://solscan.io/tx/{txn_sig}")
        return confirmed

    except Exception as e:
        print(f"Error occurred during transaction: {e}")
        return False

if __name__ == '__main__':
    mint_str = "4AvToeZjYNFMu4MyBmJErderdR3Yny9zCHfFJXqRpump"
    sell(mint_str, 100, 5)
    print("Transaction completed.")
