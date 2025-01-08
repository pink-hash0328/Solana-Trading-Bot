import asyncio
import sys
import base58
from solana.rpc.api import Client
# from solana.rpc.api import Keypair
from solders.keypair import Keypair

from solana.rpc.types import TokenAccountOpts, TxOpts
# from solders.transaction import Transaction
# from solders.transaction import Transaction as SoldersTransaction

# from solana.transaction import Transaction
from solders.transaction import Transaction

from solders.compute_budget import set_compute_unit_price, set_compute_unit_limit
from solders.system_program import transfer, TransferParams
from solders.pubkey import Pubkey
from spl.token.instructions import create_associated_token_account, SyncNativeParams
from spl.token.constants import WRAPPED_SOL_MINT, TOKEN_PROGRAM_ID, ASSOCIATED_TOKEN_PROGRAM_ID
from spl.token.instructions import sync_native
from solana.rpc.commitment import Commitment, Confirmed
from solana.rpc.async_api import AsyncClient

from solders.transaction import VersionedTransaction
from solders.message import MessageV0

from dotenv import dotenv_values
config = dotenv_values(".env")
solana_client = Client(config["RPC_HTTPS_URL"])
async_solana_client = AsyncClient(config["RPC_HTTPS_URL"])



# Initialize Solana client


private_key_string = config["PrivateKey"]
private_key_bytes = base58.b58decode(private_key_string)
payer = Keypair.from_bytes(private_key_bytes)
print(payer.pubkey())



mint_address = "So11111111111111111111111111111111111111112"

class style():
    BLACK = '\033[30m'
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'
    WHITE = '\033[37m'
    UNDERLINE = '\033[4m'
    RESET = '\033[0m'

def get_specific_token_account(owner_pubkey: str, mint_pubkey: str):
        owner_pubkey_obj = Pubkey.from_string(owner_pubkey)
        mint_pubkey_obj = Pubkey.from_string(mint_pubkey)
        opts = TokenAccountOpts(mint=mint_pubkey_obj)
        response =  solana_client.get_token_accounts_by_owner(owner_pubkey_obj, opts)
        if response.value is not None and len(response.value) > 0:
            return response.value[0].pubkey  # Return the first account found
        return None

wallet_solToken_acc= get_specific_token_account(str(payer.pubkey()),mint_address)

createWSOL_Acc = create_associated_token_account(payer.pubkey(),owner=payer.pubkey(),mint=WRAPPED_SOL_MINT)

wsol_token_account= createWSOL_Acc.accounts[1].pubkey

print(f" Your WSOL token Account: {wsol_token_account}")
# Amount of SOL to wrap (in lamports, 1 SOL = 1,000,000,000 lamports)
amount_to_wrap = int(float(config['Amount_to_Wrap']) * 10**9)
params_sync = SyncNativeParams(
    program_id=TOKEN_PROGRAM_ID,
    account=wsol_token_account
)


params = TransferParams(
    from_pubkey=payer.pubkey(),
    to_pubkey=wsol_token_account,
    lamports=amount_to_wrap
)


instructions=[]


if  wallet_solToken_acc is None:
    instructions.extend([
        createWSOL_Acc,
        transfer(params),
        sync_native(params_sync),
        set_compute_unit_price(100_750),
        set_compute_unit_limit(1_000_000)

    ])
else:
    instructions.extend([
        #createWSOL_Acc,
        transfer(params),
        sync_native(params_sync),
        set_compute_unit_price(498_750),
        set_compute_unit_limit(4_000_000)
    ])





async def send_and_confirm_transaction(client, payer, max_attempts=3):
        attempts = 0
        while attempts < max_attempts:
            try:

                compiled_message = MessageV0.try_compile(
                    payer.pubkey(),
                    instructions,
                    [],
                    client.get_latest_blockhash().value.blockhash,
                )
                print("Sending transaction...")
                txn = await async_solana_client.send_transaction(
                    txn=VersionedTransaction(compiled_message, [payer]),
                    opts=TxOpts(skip_preflight=True),
                )
                print("Transaction Signature:", txn.value)



                txid_string_sig = txn.value
                if txid_string_sig:
                    print("Transaction sent")
                    print(style.RED, f"Transaction Signature Waiting to be confirmed: https://solscan.io/tx/{txid_string_sig}" + style.RESET)
                    print("Waiting Confirmation")

                confirmation_resp = await async_solana_client.confirm_transaction(
                    txid_string_sig,
                    commitment=Confirmed,
                    sleep_seconds=0.5,
                )

                if confirmation_resp.value[0].err == None and str(
                        confirmation_resp.value[0].confirmation_status) == "TransactionConfirmationStatus.Confirmed":
                    print(style.GREEN + "Transaction Confirmed", style.RESET)
                    print(style.GREEN, f"Transaction Signature: https://solscan.io/tx/{txid_string_sig}", style.RESET)
                    return

                else:
                    print("Transaction not confirmed")
                    return False
            except asyncio.TimeoutError:
                attempts += 1
                print(f"Attempt {attempts}: Transaction not confirmed within 20 seconds. Attempting to resend.")
                print(f"Transaction signature: https://solscan.io/tx/{txid_string_sig}")
        if attempts == max_attempts:
            print("Maximum attempts reached. Transaction could not be confirmed.")


asyncio.run(send_and_confirm_transaction(solana_client, payer))