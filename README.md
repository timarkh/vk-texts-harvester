This is a Python script that downloads texts (posts and comments) written by users and groups in the Vkontakte social media platform (https://vk.com), popular in Russia and several other countries, through the API (https://vk.com/dev/apiusage). It does not perform crawling, so you will have to give it a list of URLs. (My goal was to download pages written in minority languages, which had to be manually located and verified first.) The downloaded texts are stored in JSON files, together with the sociolinguistically relevant user metadata. The script requires Python 3 (>= 3.5) with no additional modules.

Here is how you can use it:

1. First, you have to obtain your personal access token from Vkontakte, in order to have access to the API. Here's how you do it (as of May 2019):

1.1. You have to create an account there, if you don't have one already.

1.2. After you log in, you have to create something called a VK App here: https://vk.com/editapp?act=create . Choose any name you want.

1.3. Go to the settings page of your app and copy its ID and Secret key.

1.4. Get an authentication code by typing ``https://oauth.vk.com/authorize?client_id=%YOUR_APP'S_ID%&display=popup&redirect_uri=https://api.vk.com/blank.html&scope=offline&response_type=code&v=5.95`` in your browser's address bar (substituting %YOUR_APP'S_ID% for the actual ID) and copying the code from the URL you will be redirected to.

1.5. Get the access token by typing ``https://oauth.vk.com/access_token?client_id=%YOUR_APP'S_ID%&client_secret=%SECRET_KEY%&redirect_uri=https://api.vk.com/blank.html&code=%CODE_FROM_PREVIOUS_STEP%`` in the address bar and copying it from the response.

You have to store the access token to the ``config.txt`` file placed next to the script.

2. Second, you should compile a list of URLs you would like to download. The URL list should be named %LANG%_vk_urls.txt, where %LANG% should coincide with the ``lang`` parameter in the code (see below). Each URL has to be written on a separate line and look like ``https://vk.com/...``. Only group and user pages are supported (but e.g. not the event pages). All bad URLs on the list will be skipped without causing the script to crash.

3. Finally, you should edit the top-level code of the script (in the very end of it), if needed, and run it. There are two things you might want to change:

3.1. When an instance of the ``VkHarvester`` class is created, the ``lang`` parameter is passed to it. It determines the paths of the URL list and of the directory where all your JSON files are goint to be stored. Change it to whatever suits you.

3.2. The main function ``harvest()`` has an optional parameter ``overwrite_downloaded``, which is set to ``False`` by default. It means that if you resume downloading by re-running the script after it was stopped, the JSON files that already exist will not be overwritten, even if the corresponding pages have been updated since the last download. If you want the overwritten, change that parameter to ``True``.

Please bear in mind that downloading may take a lot of time, since the free VK API is limited to 3 requests per second, and batch requests for posts and comments are limited to 25 calls 100 entries each. Downloading a list of 100-200 URLs could take several days or even more, depending on the size of the pages.

The resulting pages are stored in JSONs, one per page. Each JSON has the keys ``meta`` (dictionary with the metadata) and ``posts`` (a dictionary of posts, with post IDs as keys). Each post contains a dictionary with all its comments. If a post is a repost, its contents will be stored in the ``copy_text`` field, and additionally you will see where it came from in the ``post_src_owner`` and ``copy_id`` fields. Apart from these files, the script creates two files, userData.json (user metadata) and userMentions.json (user mentions in posts), which it uses as a cache to avoid downloading the same metadata multiple times.

The script provides no anonymization. If you are going to put the data you collected online in some form, please remove all personal data in it first.

The script is partially based on a similar script written earlier by Ludmila Zaidelman (https://bitbucket.org/LudaLuda/minorlangs/src/default/) for a project headed by Boris Orekhov at HSE (http://web-corpora.net/wsgi3/minorlangs/). It was used in my project supported by the Alexander von Humboldt Foundation for developing social media corpora of minority languages of Russia. If you are going to use the script for similar academic purposes, please consider citing my paper that describes the corpus development process:

"Timofey Arkhangelskiy. 2019. Corpora of social media in minority Uralic languages. Proceedings of the fifth Workshop on Computational Linguistics for Uralic Languages, pages 125–140, Tartu, Estonia, January 7 - January 8, 2019." (Link: http://volgakama.web-corpora.net/Social_media_corpora_IWCLUL2019_final.pdf)