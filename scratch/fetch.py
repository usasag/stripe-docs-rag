import httpx
import re

html = httpx.get('https://docs.stripe.com/api/setup_intents').text

# We know the text "Find anything / Ask AI" is part of the sidebar.
# Let's see what tags surround it.
idx = html.find("Find anything / Ask AI")
if idx != -1:
    print("Found text! Context:")
    print(html[max(0, idx-500):idx+500])
else:
    print("Not found.")

# We also know "The SetupIntent object" is content.
idx2 = html.find("A SetupIntent guides you through the process")
if idx2 != -1:
    print("\n\nFound content! Context:")
    print(html[max(0, idx2-500):idx2+500])
