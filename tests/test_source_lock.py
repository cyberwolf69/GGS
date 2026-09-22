from ggs.market.source_lock import lock_price_to_beat

class Fake:
    def price_near(self,target,window,tolerance_sec=3.0):
        return {"price":81455.69,"source_ts":target+0.4,"offset_sec":0.4}

m={"_start_ts":1000,"_resolution_window_s":60}
r=lock_price_to_beat(Fake(),m)
assert r and r["price"]==81455.69
print("SOURCE_LOCK_TEST_PASS")
