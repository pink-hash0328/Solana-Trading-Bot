
import asyncio
import os
import datetime
from solana.rpc.commitment import Finalized, Confirmed
from solana.rpc.types import TxOpts
from solders.compute_budget import set_compute_unit_price, set_compute_unit_limit
from solders.message import MessageV0
from solders.pubkey import Pubkey
from solders.keypair import Keypair
from solana.rpc.async_api import AsyncClient
from solders.transaction import VersionedTransaction
from solana.rpc.api import Client
from solana.rpc import types
from spl.token.constants import TOKEN_PROGRAM_ID
from spl.token.instructions import burn, BurnParams, CloseAccountParams, close_account
from dotenv import load_dotenv
load_dotenv()
prompt= input("Do you want to close the token account? (yes/no): Stop the script if it's No, If yes press enter "
              "to continue")

payer=Keypair.from_base58_string(os.getenv("PrivateKey"))
solana_client = Client(os.getenv("RPC_HTTPS_URL"))
async_solana_client = AsyncClient(os.getenv("RPC_HTTPS_URL"))

def getTimestamp():
    while True:
        timeStampData = datetime.datetime.now()
        currentTimeStamp = "[" + timeStampData.strftime("%H:%M:%S.%f")[:-3] + "]"
        return currentTimeStamp
async def get_token_accountsCount(wallet_address: Pubkey):
    owner = wallet_address
    opts = types.TokenAccountOpts(program_id=Pubkey.from_string("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"))
    response = await async_solana_client.get_token_accounts_by_owner(owner, opts)
    return response.value

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


async def main():



      wallet_address= payer.pubkey()
      response =  await get_token_accountsCount(wallet_address)
      solana_token_accounts = {str(token_account.pubkey): token_account for token_account in response}
      tokenAccount_list= list(solana_token_accounts.keys())
      if len(tokenAccount_list)>0:
          try:
              for token in tokenAccount_list:
                  burn_instruction=[]

                  # c = await async_solana_client.get_account_info_json_parsed(Pubkey.from_string(token))
                  mint_address=Pubkey.from_string("RUpbmGF6p42AAeN1QvhFReZejQry1cLkE1PUYFVVpnL")
                  token_account=Pubkey.from_string("926MHU8vNoxS6Xcyxdqba6VMXdKjeYrTbd6ZPcRPRxzY")
                  balance = solana_client.get_token_account_balance(token_account)
                  amount=balance.value.amount
                  print(amount)

                  params = BurnParams(
                              amount=int(amount), account=token_account, mint=mint_address, owner=payer.pubkey(), program_id=TOKEN_PROGRAM_ID,
                          )

                  burn_inst= burn(params)
                  close_account_params = CloseAccountParams(account=token_account,
                                                            dest=payer.pubkey(),
                                                            owner=payer.pubkey(),
                                                            program_id=TOKEN_PROGRAM_ID)
                  instructions= []

                  instructions.extend([burn_inst,close_account(close_account_params),set_compute_unit_price(498_750), set_compute_unit_limit(4_000_000)])
                  # print(instructions)

                  msg = MessageV0.try_compile(
                     payer.pubkey(),
                     instructions,
                      [],
                      solana_client.get_latest_blockhash().value.blockhash,

                  )

                  print("Sending transaction...")
                  txn = await async_solana_client.send_transaction(
                      txn=VersionedTransaction(msg, [payer]),
                      opts=TxOpts(skip_preflight=True),
                  )
                  print("Transaction Signature:", txn.value)

                  # tx1 = VersionedTransaction(msg, [payer])
                  # txn_sig=solana_client.send_transaction(tx1)
                  # print(txn_sig.value)

                  #
                  # tokenAccount_list.remove(token)
                  txid_string_sig = txn.value

                  if txid_string_sig:
                      print("Transaction sent")
                      print(getTimestamp())
                      print(style.RED,
                            f"Transaction Signature Waiting to be confirmed: https://solscan.io/tx/{txid_string_sig}" + style.RESET)
                      print("Waiting Confirmation")
                  block_height = solana_client.get_block_height(Confirmed).value
                  print(f"Block height: {block_height}")

                  confirmation_resp = solana_client.confirm_transaction(
                      txid_string_sig,
                      commitment=Confirmed,
                      sleep_seconds=0.5,
                      last_valid_block_height=block_height + 50
                  )
                  print(confirmation_resp)

                  if confirmation_resp.value[0].err == None and str(
                          confirmation_resp.value[0].confirmation_status) == "TransactionConfirmationStatus.Confirmed":
                      print(getTimestamp())

                      print(style.GREEN + "Transaction Confirmed", style.RESET)
                      print(f"Transaction Signature: https://solscan.io/tx/{txid_string_sig}")

                      return

                  else:
                      print("Transaction not confirmed")
                      return False


          except Exception as e:
                print(e)
                # continue


asyncio.run(main())