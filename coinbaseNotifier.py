import json, hmac, hashlib, time, requests, base64, hashlib, os
from datetime import datetime
from requests.auth import AuthBase

# Setting variables from Environment Variables
api_key = os.environ.get('coinbase_api_key')
secret = os.environ.get('coinbase_secret')
passphrase = os.environ.get('coinbase_passphrase')
discord_webhook_url = os.environ.get('discord_webhook_url')

# Coinbase Pro authentication
class CoinbaseExchangeAuth(AuthBase):
    def __init__(self, api_key, secret_key, passphrase):
        self.api_key = api_key
        self.secret_key = secret
        self.passphrase = passphrase

    def __call__(self, request):
        timestamp = str(time.time())
        message = timestamp + request.method + request.path_url + (request.body or '')
        message = message.encode('ascii')                                                   ## Needed for Python3
        hmac_key = base64.b64decode(self.secret_key)
        signature = hmac.new(hmac_key, message, hashlib.sha256)
        signature_b64 = base64.b64encode(signature.digest()).decode('utf-8')                ## Needed for Python3

        request.headers.update({
            'CB-ACCESS-SIGN': signature_b64,
            'CB-ACCESS-TIMESTAMP': timestamp,
            'CB-ACCESS-KEY': self.api_key,
            'CB-ACCESS-PASSPHRASE': self.passphrase,
            'Content-Type': 'application/json'
        })
        return request

api_url = 'https://api.pro.coinbase.com/'
auth = CoinbaseExchangeAuth(api_key, secret, passphrase)

# Checking for new orders that change status to settled and sending message. Sleeps for 32 seconds between checks.
orders = dict()
while(1):
    # Set Variables
    now = datetime.now()
    orderIndex = 0
    params = {'status':'done'}

    # Load JSON
    response = requests.get(api_url + 'orders', auth=auth, params=params)
    allOrders = json.loads(response.text)

    # Checks to see if Coinbase Pro API IP is correct
    # if(allOrders['message'] == 'IP does not match IP whitelist'):
    #         print("Update whitelisted IP for Coinbase API")
    
    # Checks to see if newest order already in dictionary, otherwise add it
    for index, order in enumerate(allOrders):
        if (not(allOrders[0]['id'] in orders.values())):
            if (allOrders[0]['settled'] == True):
                orders.update({'%d'%index: allOrders[index]['id']})
                params = {'order_id':allOrders[0]['id']}
                response = requests.get(api_url + 'fills', auth=auth, params=params)
                newestOrder = json.loads(response.text)

                product_id = newestOrder[0]['product_id']
                price = newestOrder[0]['price']
                size = newestOrder[0]['size']
                fee = newestOrder[0]['fee']

                price = float(price)
                size = float(size)
                fee = float(fee)
                orderCost = ((price * size) - fee)

                data = {
                    "username" : "Coinbase Pro",
                }
                data["embeds"] = [
                    {
                        "title" : "New Order Has Been Filled",
                        "description" : "Coin Purchased: " + product_id + 
                            "\nPrice Per Coin: $%.2f" % price +
                            "\nQuantity Purchased: %f" % size +
                            "\nFee: $%0.3f" % fee +
                            "\nCost Of Amount Purchased: $%.2f" % round(orderCost, 2)
                    }
                ]
                result = requests.post(discord_webhook_url, json = data)

                print("New Order Has Been Filled:")
                print("Coin Purchased: " + product_id)
                print("Price Per Coin: $%.2f" % price)
                print("Quantity Purchased: %f" % size)
                print("Fee: $%0.3f"%fee)
                print("Cost Of Amount Purchased: $%.2f" % round(orderCost, 2))
                break
    time.sleep(61)
