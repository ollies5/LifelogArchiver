# LifelogArchiver
Grabs and stores *all* of your Limitless lifelogs recursively using their API.
> [!IMPORTANT]
>Limitless currently only offers the API to those with Pendant lifelogs (the physical device), so this script will not work for other transcripts, like meetings on the desktop app.

# Usage
1) Download everything
2) Be sure to install all dependencies from the requirements.txt or by running:

```
pip install requests tzlocal tqdm
```
3) Run the .py
4) You'll need your Limitless API key, which you can find out how to get [here](https://www.limitless.ai/developers). Paste it into the script when prompted.
5) Once it's done, everything will be saved to `all_lifelogs.txt` in the same directory the script is saved in.

It might take a while to run, depending on how many lifelogs you have. Unfortunately, there is no way to estimate how long it will take with the current API.
