import tweepy

# =========================
# Fill in your keys here
# =========================
TWITTER_API_KEY = "5f0bm7d8t1tYyqslNMgJXHb2J"
TWITTER_API_SECRET = "vQf3LCa5FFE83FBMNf2A6D6a3TMjDmQ5GGH1XRd6vAKeHzkD3U"
TWITTER_ACCESS_TOKEN = "2018301449252339712-dJAWv3v9goEwRZFv1vKZKDVTvnhuPd"
TWITTER_ACCESS_SECRET = "hlRXyoE0NMtU5IcwYUzqASQDp7gS8t8HlD454R8xt24tS"


# =========================
# Test Script
# =========================
def test_x_api():
    try:
        # Create Tweepy v2 client
        client = tweepy.Client(
            consumer_key=TWITTER_API_KEY,
            consumer_secret=TWITTER_API_SECRET,
            access_token=TWITTER_ACCESS_TOKEN,
            access_token_secret=TWITTER_ACCESS_SECRET,
        )

        # Fetch your own account info
        user = client.get_me()
        print("✅ Twitter/X API authentication OK")
        print(f"Authenticated as: {user.data.username} ({user.data.id})")

        # Try simulating a tweet
        test_tweet = "This is a test tweet from my local dev environment."
        try:
            client.create_tweet(text=test_tweet)
            print("✅ Tweet posted successfully (check your account).")
        except tweepy.errors.Forbidden:
            print("⚠ X API restriction detected. Simulating tweet instead:")
            print(f"[SIMULATED TWEET]\n{test_tweet}")
        except tweepy.errors.TooManyRequests:
            print("⚠ Rate limit exceeded. Tweet not posted.")

    except Exception as e:
        print(f"❌ Error connecting to X API: {e}")


if __name__ == "__main__":
    test_x_api()
