import time
import requests
import json

class Miner:
    def __init__(self, rpc_url, miner_address="network_miner"):
        self.rpc_url = rpc_url
        self.miner_address = miner_address
        self.got_job_last_time = False

    def set_data(self, rpc_url, miner_address):
        self.rpc_url = rpc_url
        self.miner_address = miner_address  

    def get_job(self):
        response = requests.get(self.rpc_url+'mining/get')
        try:
            return response.json()
        except:
            print(response.text)

    def get_block_number(self):
        response = requests.post(self.rpc_url+'rpc/', json={
            "jsonrpc": "2.0",
            "method": "eth_blockNumber",
            "id": 1
        })
        return response.json()

    def get_tx_by_number(self, block_number):
        response = requests.post(self.rpc_url+'rpc/', json={
            "jsonrpc": "2.0",
            "method": "eth_getTransactionByNumber",
            "params": [hex(block_number), True],
            "id": 1
        })
        return response.json()

    def submit_mined(self, mined_txs):
        response = requests.post(self.rpc_url+'mining/submit', json={
            "miner": self.miner_address,
            "mined_data": mined_txs,
        })
        return response

    def mine(self):
        job = self.get_job()
        if job == "NO_JOB":
            if self.got_job_last_time == False:
                requests.post('http://127.0.0.1:3469/set_speed', json={"speed": 0.0})
            self.got_job_last_time = False
            return
        self.got_job_last_time = True
        # Start processing the job
        pending_txs = job["transactions"]
        
        mined_txs = {}
        for tx in pending_txs:
            tx_hash = tx["hash"]
            parent_hashes = self.find_parents(tx)  # Find parents for the current transaction
            if parent_hashes:
                mined_txs[tx_hash] = parent_hashes
        # Submit mined transactions
        if mined_txs:
            submit_response = self.submit_mined(mined_txs)
            requests.post('http://127.0.0.1:3469/set_submissions', json={"code": submit_response.status_code, "message": submit_response.json().get("message")})
        else:
            pass # No valid transactions mined.
        
    def find_parents(self, tx):
        parents = []
        juice_needed = int(tx["amount"]+tx["gas"])
        latest_block = int(self.get_block_number()["result"], 16)

        starttraversal = time.time_ns()
        for ptx_n in range(0, latest_block+1): # must go till block number thus +1
            ptx = self.get_tx_by_number(ptx_n)["result"]
            if ptx: # ptx = parent transaction,  tx = child transaction
                if ptx["recipient"] == tx["sender"]:
                    juice = int(ptx["juice"])
                    if juice >= juice_needed:
                        parents.append(ptx["hash"])
                        juice_needed = 0
                    elif juice > 0:
                        parents.append(ptx["hash"])
                        juice_needed -= juice
                    if juice_needed == 0:
                        break
        endtraversal = time.time_ns()
        timetaken = (endtraversal-starttraversal) / (1e+9) # ns to s
        traversalspeed = 1/(timetaken)
        result = parents if juice_needed == 0 else []
        requests.post('http://127.0.0.1:3469/set_speed', json={"speed": traversalspeed})
        return result

if __name__ == '__main__':
    rpc_url = "https://xyl-testnet.glitch.me/"
    miner = Miner(rpc_url)
    while True:
        miner.mine()
        time.sleep(1)
