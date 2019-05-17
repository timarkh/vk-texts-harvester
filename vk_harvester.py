import urllib.request as requests
import urllib.parse as parse
import re
import datetime
import json
import os
import time
import copy


class VkHarvester:
    """
    Class with methods for harvesting linguictic data and metadata
    from vk.com using their API.
    """
    rxVkId = re.compile('\\[((?:id|club)[0-9]+)\\|([^\r\n\\[\\]]+)\\]')

    def __init__(self, lang):
        self.lang = lang
        # In order to use the vk API, you have to register your own
        # app and get an acces token. The token should be stored in
        # config.txt as plain text.
        try:
            with open('config.txt', 'r', encoding='utf-8') as fAccessToken:
                self.access_token = fAccessToken.read()
                if '\n' in self.access_token:
                    self.access_token = re.sub('\n.*', '', self.access_token, flags=re.DOTALL)
        except OSError:
            print('Could not load the access token.')
            self.access_token = ''
        self.urls = self.get_urls()
        self.request_count = 0
        self.n_batch_calls = 25
        # Each time a user or a group is mentioned, the text of
        # the mention is stored in userMentions.json. This information
        # is not important for the processing, so if you do not need
        # this, you can safely switch this off.
        try:
            with open('userMentions.json', 'r', encoding='utf-8') as fVkDescs:
                self.userMentions = json.loads(fVkDescs.read())
        except FileNotFoundError:
            print('Warning: could not load vk user descriptions.')
            self.userMentions = {}
            fEmpty = open('userMentions.json', 'w', encoding='utf-8')
            fEmpty.write('{}')
            fEmpty.close()
        for k in self.userMentions:
            self.userMentions[k] = set(self.userMentions[k])
        # User metadata is stored in userData.json. For each user,
        # the metadata is only loaded once.
        try:
            with open('userData.json', 'r', encoding='utf-8') as fVkData:
                self.userMetadata = json.loads(fVkData.read())
        except FileNotFoundError:
            print('Warning: could not load vk user data.')
            self.userMetadata = {}
            fEmpty = open('userData.json', 'w', encoding='utf-8')
            fEmpty.write('{}')
            fEmpty.close()

    def get_urls(self):
        """
        Read all URLs of vk pages from a plain-text list.
        """
        urls = set()
        fileAddr = self.lang + '_vk_urls.txt'
        print('Reading URLs from the list:')
        with open(fileAddr, 'r', encoding='utf-8-sig') as fIn:
            for line in fIn:
                values = line.rstrip().split(',')
                urlFull = re.search('^https?://vk\\.com/([^?]*)', values[0])
                if urlFull is not None:
                    url = re.sub('^public', 'club', urlFull.group(1))
                    urls.add(url)
        urls = [url for url in sorted(urls)]
        print(urls)
        print('Finshed reading URLs.')
        return urls

    def make_dir(self):
        """
        Create directories for the texts to be harvested.
        """
        if not os.path.exists(self.lang):
            os.makedirs(self.lang)
        if not os.path.exists(self.lang + '/users'):
            os.makedirs(self.lang + '/users')

    def save_user_ids(self, fname_mentions='userMentions.json', fname_userdata='userData.json'):
        """
        Write information about vk user IDs mentioned in the groups.
        """
        for k in self.userMentions:
            self.userMentions[k] = [username for username in sorted(self.userMentions[k])]
        jsonVkMentions = json.dumps(self.userMentions,
                                    ensure_ascii=False,
                                    indent=2,
                                    sort_keys=True)
        jsonVkData = json.dumps(self.userMetadata,
                                ensure_ascii=False,
                                indent=2,
                                sort_keys=True)
        with open(fname_mentions, 'w', encoding='utf-8') as fVkDesc:
            fVkDesc.write(jsonVkMentions)
        with open(fname_userdata, 'w', encoding='utf-8') as fVkData:
            fVkData.write(jsonVkData)
        for k in self.userMentions:
            self.userMentions[k] = set(self.userMentions[k])

    def enhance_user_data(self):
        """
        Add lacking fields to the user metadata loaded from userData.json.
        This functions only has to be called if the user data was collected
        using a previous version of the harvester.
        """
        userIDs = list(self.userMetadata.keys())
        completeUserData = self.get_users(userIDs)
        self.userMetadata = {user['id']: user for user in completeUserData}
        print('User data successfully enhanced.')

    def extract_info(self, text):
        """
        Extract info like vk IDs of the users or communities
        mentioned in the text of a post or a comment.
        """
        mentions = self.rxVkId.findall(text)
        for m in mentions:
            if m[0] not in self.userMentions:
                self.userMentions[m[0]] = set()
            self.userMentions[m[0]].add(m[1].strip().lower())

    def get_response(self, url, params):
        """
        Send an HTTP query, sleep a little after every 1000 queries.
        """
        paramsEncoded = parse.urlencode(params)
        if self.request_count == 1000:
            self.request_count = 0
            time.sleep(100)
        # Free vk API has a limit of 3 requests per second.
        time.sleep(0.35)
        urlFull = url + '?' + paramsEncoded
        try:
            if 'v' not in params:
                urlFull += '&v=5.95'
            if 'access_token' not in params:
                urlFull += '&access_token=' + self.access_token
            # print(urlFull)
            entity = requests.urlopen(urlFull).read()
            entity = json.loads(str(entity.decode()))
            return entity
        except:
            print('Error when retrieving a URL:', urlFull)
            # return get_response(url, params)
            return None

    def get_account_extended(self, method, fields, id_field, ids):
        """
        Retrieve user or group data by user/group IDs. The URL specifies
        the API function to be used (groups and users are served by different
        functions).
        """
        result = []
        for iRange in range(len(ids) // 200 + 1):
            parameters = {id_field: ','.join(str(i) for i in ids[iRange * 200:(iRange + 1) * 200]),
                          'fields': fields}
            accountData = self.get_response('https://api.vk.com/method/' + method, parameters)
            if 'response' in accountData:
                result += accountData['response']
            else:
                print(method, ': Error when retrieveing account data:', parameters, accountData)
        return result

    def get_users(self, ids):
        """
        Retrieve vk user data by user IDs.
        """
        fields = 'sex, bdate, city, country, home_town, '\
                 'career, domain, education, '\
                 'followers_count, occupation, '\
                 'schools, screen_name, universities'
        return self.get_account_extended('users.get', fields, 'user_ids', ids)

    def get_groups_extended(self, ids):
        """
        Retrieve vk group data by group IDs.
        """
        fields = 'members_count'
        return self.get_account_extended('groups.getById', fields, 'group_ids', ids)

    def get_user(self, user_id):
        """
        Retrieve vk user data by user ID.
        """
        arrData = self.get_users([user_id])
        if arrData is None or len(arrData) <= 0:
            return None
        return arrData[0]

    def leave_essential_data(self, user):
        """
        Return a shortened dictionary describing a user, only with
        the keys that need to be saved in json files.
        """
        newUserDict = {'id': user['id'], 'first_name': user['first_name'],
                       'last_name': user['last_name'], 'sex': user['sex']}
        if 'city' in user:
            newUserDict['city'] = user['city']['title']
        if 'bdate' in user:
            newUserDict['bdate'] = user['bdate']
        if 'home_town' in user:
            newUserDict['home_town'] = user['home_town']
        return newUserDict

    def get_author(self, message_json, account_dict):
        """
        Check if the post author is a user or a group (groups have negative IDs).
        Return its data. Use cache.
        """
        if 'from_id' not in message_json:
            print('No from_id in message:', json.dumps(message_json))
            return {}
        authorID = message_json['from_id']
        if authorID == account_dict['meta']['id'] * -1 or authorID == account_dict['meta']['id']:
            return account_dict['meta']['screen_name']
        elif authorID > 0:
            if str(authorID) in self.userMetadata:
                return self.leave_essential_data(self.userMetadata[str(authorID)])
            author = self.get_user(authorID)
            if author is not None:
                self.userMetadata[str(authorID)] = author
            else:
                author = {}
            return self.leave_essential_data(author)
        return {}

    def execute_code(self, offset, command, n_msg):
        """
        Generate a VKScript code snippet to send via the execute API function.
        The script makes up to self.n_batch_calls calls to get the posts consecutively.
        offset: offset of the post to start with
        command: a string with a single API call
        n_msg: number of messages to download
        """
        # No more than 25 API calls are allowed within one Execute script.
        return ('var objs = [];' +
                'var offset = 0;' +
                # read while the call limit is exceeded or all messgaes have been harvested
                'while (offset < ' + str(self.n_batch_calls * 100) +
                ' && (offset + ' + str(offset * 100) + ') < ' + str(n_msg) + ')' +
                '{' +
                'objs = objs + ' + command + ', "count": "100", "offset": offset + ' +
                str(offset * 100) + '}).items;' +
                'offset = offset + 100;' +
                '};' +
                'return objs;')

    def write_comment(self, comment, account_dict, ps_id):
        """
        Add a comment to the post identified by ps_id stored in group_dict.
        """
        # print(comment)
        comm_date = str(datetime.datetime.fromtimestamp(comment['date']))
        comm_author = self.get_author(comment, account_dict)
        if len(comm_author) <= 0 or 'text' not in comment:
            return
        self.extract_info(comment['text'])
        account_dict['posts'][ps_id]['comments'][comment['id']] = {'date': comm_date,
                                                                   'text': comment['text'],
                                                                   'author': comm_author,
                                                                   'sort': comment['date']}

    def get_comments(self, ps, account_dict, is_group=True):
        """
        Retrieve all comments to a given post ps in the group gr.
        """
        offset = 0              # comment number offset, in hundreds
        accountId = account_dict['meta']['id']
        if is_group:
            accountId *= -1     # Groups have negative IDs
        par_comm = {'owner_id': accountId, 'post_id': ps['id'], 'count': '0'}
        comm = self.get_response('https://api.vk.com/method/wall.getComments', par_comm)
        # print(comm)
        if 'response' in comm:
            comm_num = comm['response']['count']
            print('post', ps['id'], ':', comm_num, 'comments will be loaded.')
            off_n = comm_num // 100 + 1
            while offset < off_n:
                # print('Getting a comment...')
                command = 'API.wall.getComments({"owner_id": ' +\
                          str(accountId) +\
                          ', "post_id": ' + str(ps['id'])
                code = self.execute_code(offset, command, comm_num)
                comm = self.get_response('https://api.vk.com/method/execute',
                                         {'code': code, 'access_token': self.access_token})
                # print('comment:', comm)
                if 'response' in comm:
                    for j in range(len(comm['response'])):
                        self.write_comment(comm['response'][j], account_dict, ps['id'])
                offset += self.n_batch_calls
                time.sleep(0.5)

    def write_post(self, wall, n_post, account_dict, write_reposts=True, is_group=True):
        """
        Add a post from the wall with the index n_post to the account stored in account_dict.
        If write_reposts is False, do not save the text of reposted messages.
        """
        ps = wall[n_post]
        # print(ps)
        try:
            post_date = str(datetime.datetime.fromtimestamp(ps['date']))
        except OSError:
            post_date = ''
        except TypeError:
            return
        postCopyText = ''
        postSource = ''
        postCopyId = ''
        if 'copy_history' in ps:
            postCopyText = ps['copy_history'][0]['text']
            postSource = ps['copy_history'][0]['owner_id']
            postCopyId = ps['copy_history'][0]['id']
        postAuthor = self.get_author(ps, account_dict)
        self.extract_info(ps['text'])
        account_dict['posts'][ps['id']] = {'date': post_date,
                                           'text': ps['text'],
                                           'author': postAuthor,
                                           'comments': {},
                                           'sort': ps['date']}
        if len(postCopyText) > 0:
            self.extract_info(postCopyText)
            if write_reposts:
                account_dict['posts'][ps['id']]['copy_text'] = postCopyText
            account_dict['posts'][ps['id']]['copy_id'] = postCopyId
            account_dict['posts'][ps['id']]['post_src_owner'] = postSource
        if 'comments' in ps and 'count' in ps['comments'] and ps['comments']['count'] > 0:
            self.get_comments(ps, account_dict, is_group)

    def get_posts(self, account_dict, is_group=True):
        """
        Get all posts and comments of a single group or user. If is_group
        is True, treat the account as a group, otherwise as a user.
        """
        offset = 0              # post number offset, in hundreds
        self.n_batch_calls = 25
        accountId = account_dict['meta']['id']
        writeReposts = False
        if is_group:
            accountId *= -1     # Groups have negative IDs
            writeReposts = True
        parameters = {'owner_id': accountId, 'count': '0'}
        wall = self.get_response('https://api.vk.com/method/wall.get', parameters)
        if 'response' not in wall:
            print('Something went wrong when trying to download the account', account_dict['meta']['id'],
                  ':', wall)
            return
        nPosts = wall['response']['count']
        print(nPosts, 'posts on the wall.')
        offHundreds = nPosts // 100 + 1
        while offset < offHundreds:
            print('Getting posts...')
            command = 'API.wall.get({"owner_id": ' + str(accountId)
            wall = None
            while wall is None or 'error' in wall:
                code = self.execute_code(offset, command, nPosts)
                wall = self.get_response('https://api.vk.com/method/execute',
                                         {'code': code, 'access_token': self.access_token})
                if wall is None or 'error' in wall:
                    # Each response contains at most 2500 enrties (25 calls, 100 entries each),
                    # but if that turns out to be too much for vk to process, try reducing
                    # the number of calls per request.
                    print(wall)
                    self.n_batch_calls -= 5
                    if self.n_batch_calls < 5:
                        print('Could not download account', account_dict['meta']['screen_name'])
                        return
            if 'response' in wall and len(wall['response']) > 0:
                for j in range(len(wall['response'])):
                    self.write_post(wall['response'], j, account_dict,
                                    write_reposts=writeReposts, is_group=is_group)
            offset += self.n_batch_calls
            time.sleep(0.5)

    def process_group(self, gr, overwrite_downloaded=True):
        """
        Download a group and return all posts and comments as a dictionary.
        gr: group metadata
        """
        print('Starting group', gr, '...')
        date_start = datetime.datetime.today()
        filename = self.lang + '/' + gr['screen_name'] + '.json'
        if os.path.exists(filename):
            print('File for the group', gr['screen_name'], 'already exists.')
            if not overwrite_downloaded:
                return
        if gr['is_closed'] == 2:
            print(gr['screen_name'], 'does not exist.')
            return
        group_dict = {'meta': {}, 'posts': {}}
        group_dict['meta'] = {'id': gr['id'],
                              'name': gr['name'],
                              'screen_name': gr['screen_name'],
                              'members_count': gr['members_count'],
                              'language': self.lang,
                              'date': str(datetime.datetime.today())}
        if gr['is_closed'] == 1:
            print(gr['screen_name'], 'is a closed group.')
            return
        self.get_posts(group_dict, is_group=True)
        with open(filename, 'w', encoding='utf-8') as groupDump:
            json.dump(group_dict, groupDump, ensure_ascii=False, indent=2, sort_keys=True)
        self.save_user_ids()
        print('Group', gr['screen_name'], 'harvested in', str(datetime.datetime.today() - date_start))

    def process_user(self, user, overwrite_downloaded=True):
        """
        Download the user's wall and return all posts and comments as a dictionary.
        user: user metadata
        """
        if 'screen_name' not in user:
            if 'deactivated' in user:
                print('User is deactivated:', user)
                return
            if 'hidden' in user:
                print('User is hidden:', user)
                return
            print('No screen name for the user:', user)
            return
        print('Starting user', user['screen_name'], '...')
        date_start = datetime.datetime.today()
        filename = self.lang + '/users/' + user['screen_name'] + '.json'
        if os.path.exists(filename):
            print('File for the user', user['screen_name'], 'already exists.')
            if not overwrite_downloaded:
                return
        user_dict = {'meta': copy.deepcopy(user), 'posts': {}}
        user_dict['meta']['language'] = self.lang,
        user_dict['meta']['date'] = str(datetime.datetime.today())
        self.get_posts(user_dict, is_group=False)
        with open(filename, 'w', encoding='utf-8') as userDump:
            json.dump(user_dict, userDump, ensure_ascii=False, indent=2, sort_keys=True)
        self.save_user_ids()
        print('User', user['screen_name'], 'harvested in', str(datetime.datetime.today() - date_start))

    def harvest(self, overwrite_downloaded=False):
        """
        Download contents of the groups and the users' walls, using
        a list of URLs located in %self.lang%_vk_urls.txt. If overwrite_downloaded
        is False, skip groups and users for which there already exists
        a JSON file.
        """
        print('Harvesting started.')
        print('Harvesting groups first...')
        personalUrls = set(url.strip() for url in harvester.urls
                           if not url.startswith('club'))
        groups = harvester.get_groups_extended(harvester.urls)
        for i in range(len(groups)):
            if groups[i]['screen_name'] in personalUrls:
                personalUrls.remove(groups[i]['screen_name'])
            harvester.process_group(groups[i], overwrite_downloaded=overwrite_downloaded)
        print('Group harvesting finished.')
        print('Harvesting users...')
        personalUrls = list(personalUrls)
        print('Personal URLs:', ','.join(personalUrls))
        users = self.get_users(personalUrls)
        for i in range(len(users)):
            harvester.process_user(users[i], overwrite_downloaded=overwrite_downloaded)
        print('Harvesting finished.')


if __name__ == '__main__':
    date_start = datetime.datetime.today()
    harvester = VkHarvester('mhr')
    harvester.make_dir()
    harvester.harvest()
    # harvester.enhance_user_data()
    # harvester.save_user_ids()
    print('Elapsed time:', str(datetime.datetime.today() - date_start))
