import asyncio
import datetime
import time
from solana.rpc.types import TokenAccountOpts, TxOpts
from solders.message import MessageV0
from solders.pubkey import Pubkey
from solana.rpc.commitment import Commitment, Confirmed
from solana.rpc.api import RPCException
from solana.rpc.api import Client
from solders.keypair import Keypair

from solana.rpc.async_api import AsyncClient
from solders.compute_budget import set_compute_unit_price,set_compute_unit_limit
from solders.transaction import  VersionedTransaction
from utils.create_close_account import   get_token_account, make_swap_instruction ,sell_get_token_account
from utils.birdeye import getSymbol
from utils.pool_information import gen_pool, getpoolIdByMint
import os
from dotenv import load_dotenv

load_dotenv()
RPC_HTTPS_URL= os.getenv("RPC_HTTPS_URL")
solana_client = Client(os.getenv("RPC_HTTPS_URL"))
async_solana_client = AsyncClient(os.getenv("RPC_HTTPS_URL"))
payer=Keypair.from_base58_string(os.getenv("PrivateKey"))
Wsol_TokenAccount=os.getenv('WSOL_TokenAccount')

AMM_PROGRAM_ID = Pubkey.from_string('675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8')
SERUM_PROGRAM_ID = Pubkey.from_string('srmqPvymJeFKQ4zGQed1GFppgkRHL9kaELCbyksJtPX')
LAMPORTS_PER_SOL = 1000000000
MAX_RETRIES = 5
RETRY_DELAY = 3


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

def getTimestamp():
    while True:
        timeStampData = datetime.datetime.now()
        currentTimeStamp = "[" + timeStampData.strftime("%H:%M:%S.%f")[:-3] + "]"
        return currentTimeStamp




async def sell(solana_client, TOKEN_TO_SWAP_SELL, payer):
    retry_count = 0
    while retry_count < MAX_RETRIES:
        try:
            token_symbol, SOl_Symbol = getSymbol(TOKEN_TO_SWAP_SELL)
            mint = Pubkey.from_string(TOKEN_TO_SWAP_SELL)

            # mint= TOKEN_TO_SWAP_SELL
            sol = Pubkey.from_string("So11111111111111111111111111111111111111112")
            TOKEN_PROGRAM_ID = solana_client.get_account_info_json_parsed(mint).value.owner

            try:

                tokenPool_ID = await getpoolIdByMint(mint, AsyncClient(RPC_HTTPS_URL, commitment=Confirmed))

                if tokenPool_ID:

                    fetch_pool_key = await gen_pool(str(tokenPool_ID), AsyncClient(RPC_HTTPS_URL, commitment=Confirmed))
                    pool_keys = fetch_pool_key
                    # print(pool_keys)
                else:
                    print("AMMID NOT FOUND SEARCHING WILL BE FETCHING WITH RAYDIUM SDK.. THis happens")

            except Exception as e:
                print(e)




            opts = TokenAccountOpts(mint=mint)
            response = await async_solana_client.get_token_accounts_by_owner(payer.pubkey(), opts)
            tokenAccount = response.value[0].pubkey
            balance = await async_solana_client.get_token_account_balance(tokenAccount, commitment=Confirmed)


            amount_in = balance.value.amount

            print("Token Balance : ", amount_in)

            if int(amount_in) == 0:
                return "NO BALANCE"


            swap_token_account = sell_get_token_account(solana_client, payer.pubkey(), mint)
            WSOL_token_account, WSOL_token_account_Instructions = get_token_account(solana_client, payer.pubkey(), sol)

            print("3. Create Swap Instructions...")
            instructions_swap = make_swap_instruction(amount_in,
                                                      swap_token_account,
                                                      WSOL_token_account,
                                                      pool_keys,
                                                      mint,
                                                      solana_client,
                                                      payer
                                                      )

            swap_tx = []
            if WSOL_token_account_Instructions != None:
                swap_tx.append(WSOL_token_account_Instructions)

            swap_tx.extend([instructions_swap,
                            set_compute_unit_price(498_750),
                            set_compute_unit_limit(4_000_000)])

            print("Execute Transaction...")
            compiled_message = MessageV0.try_compile(
                payer.pubkey(),
                swap_tx,
                [],
                solana_client.get_latest_blockhash().value.blockhash,
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
                print(getTimestamp())
                print(style.RED,f"Transaction Signature Waiting to be confirmed: https://solscan.io/tx/{txid_string_sig}"+style.RESET)
                print("Waiting Confirmation")
            block_height = solana_client.get_block_height(Confirmed).value
            print(f"Block height: {block_height}")

            confirmation_resp = solana_client.confirm_transaction(
                txid_string_sig,
                commitment=Confirmed,
                sleep_seconds=0.5,
                last_valid_block_height=block_height + 100
            )

            if confirmation_resp.value[0].err == None and str(
                    confirmation_resp.value[0].confirmation_status) == "TransactionConfirmationStatus.Confirmed":
                print(getTimestamp())

                print(style.GREEN+"Transaction Confirmed",style.RESET)
                print(f"Transaction Signature: https://solscan.io/tx/{txid_string_sig}")

                return

            else:
                print("Transaction not confirmed")
                return False
        except asyncio.TimeoutError:
            print("Transaction confirmation timed out. Retrying...")
            retry_count += 1
            time.sleep(RETRY_DELAY)
        except RPCException as e:
            print(f"RPC Error: [{e.args[0].message}]... Retrying...")
            retry_count += 1
            time.sleep(RETRY_DELAY)
        except Exception as e:
            print(f"Unhandled exception: {e}. Retrying...")
            retry_count += 1
            time.sleep(RETRY_DELAY)

    print("Failed to confirm transaction after maximum retries.")
    return False

async def main():

    token_toSell="3WdmE9BAHgVyB1JNswSUcj6RmkxnsvfJTd6RFnQ4pump"
    print(payer.pubkey())
    await sell(solana_client, token_toSell, payer)

asyncio.run(main())