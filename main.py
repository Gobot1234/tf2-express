from time import sleep

from express.logging import Log, f
from express.prices import get_price, get_pricelist
from express.client import Client
from express.trades import add
from express.offer import Offer
from express.utils import Items, to_scrap, to_refined

client = Client()
client.login()

processed = []
values = {}

while True:
    offers = client.get_offers()  

    for offer in offers:
        offer_id = offer['tradeofferid']

        if offer_id not in processed:
            log = Log(offer_id)

            trade = Offer(offer)
            steam_id = trade.get_partner()

            if trade.is_active() and not trade.is_our_offer():
                log.trade(f'Received a new offer from {f.YELLOW + str(steam_id)}')

                if trade.is_gift():
                    log.trade('User is trying to give items')
                    client.accept(offer_id)

                elif trade.is_scam():
                    log.trade('User is trying to take items')
                    client.decline(offer_id)

                elif trade.is_valid():
                    log.trade('Processing offer...')
                    
                    their_value = 0
                    their_items = offer['items_to_receive']

                    our_value = 0
                    our_items = offer['items_to_give']

                    prices = get_pricelist()

                    # Their items
                    for _item in their_items:
                        item = Items(their_items[_item])
                        name = item.name
                        value = 0.00

                        if item.is_tf2():
                            
                            if item.is_pure():
                                value = item.get_pure()

                            elif item.is_craftable():

                                if name in prices:
                                    value = get_price(name, 'buy')

                                elif item.is_craft_hat():
                                    value = get_price('Random Craft Hat', 'buy')
                                
                            elif not item.is_craftable():
                                name = 'Non-Craftable ' + name
                                
                                if name in prices:
                                    value = get_price(name, 'buy')
                        
                        their_value += to_scrap(value)

                    # Our items
                    for _item in our_items:
                        item = Items(our_items[_item])
                        name = item.name
                        value = 0.00
                        high = float(10**5)

                        if item.is_tf2():
                            
                            if item.is_pure():
                                value = item.get_pure()

                            elif item.is_craftable():
                            
                                if name in prices:
                                    value = get_price(name, 'sell')

                                elif item.is_craft_hat():
                                    value = get_price('Random Craft Hat', 'sell')
                                
                                else:
                                    value = high
                                
                            elif not item.is_craftable():
                                name = 'Non-Craftable ' + name

                                if name in prices:
                                    value = get_price(name, 'sell')
                                
                                else:
                                    value = high
                            
                            else:
                                value = high

                        else:
                            value = high
                    
                        our_value += to_scrap(value)
                    
                    item_amount = len(their_items) + len(our_items)
                    log.trade(f'Offer contains {item_amount} items')

                    difference = to_refined(their_value - our_value)
                    their_value = to_refined(their_value)
                    our_value = to_refined(our_value)
                    summary = 'User value: {} ref, our value: {} ref, difference: {} ref'

                    log.trade(summary.format(their_value, our_value, difference))

                    if to_scrap(their_value) >= to_scrap(our_value):
                        values[offer_id] = {
                            'our_value': our_value,
                            'their_value': their_value
                        }
                        client.accept(offer_id)

                    else:
                        client.decline(offer_id)

                else:
                    log.trade('Offer is invalid or user has trade hold')
                    client.decline(offer_id)

            else:
                log.trade('Offer is not active')
        
            processed.append(offer_id)
    
    del offers

    for offer_id in processed:
        offer = client.get_offer(offer_id)
        trade = Offer(offer)

        log = Log(offer_id)

        if not trade.is_active():
            state = trade.get_state()
            log.trade(f'Offer changed state to {f.YELLOW + state}')

            if trade.is_accepted() \
                and 'tradeid' in offer:
                log.info('Saving offer data...')
                _values = {}

                if offer_id in values:
                    _values = values[offer_id]

                trade_id = offer['tradeid']
                receipt = client.get_receipt(trade_id)

                offer['receipt'] = receipt
                offer['values'] = _values
                offer.pop('items_to_give')
                offer.pop('items_to_receive')

                add(offer)
                
                log.info('Offer was saved')
                values.pop(offer_id)

                del _values

            processed.remove(offer_id)

    sleep(30)
