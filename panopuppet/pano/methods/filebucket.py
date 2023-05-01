import requests
import hashlib
import difflib

from panopuppet.pano.puppetdb.puppetdb import api_get as pdb_api_get, get_server, mk_puppetdb_query

__author__ = 'takeshi'

requests.packages.urllib3.disable_warnings()


def get_hash(data):
    m = hashlib.md5()
    m.update(data.encode('utf-8'))
    return m.hexdigest()


def get_file(request, certname, environment, rtitle, rtype, md5sum_from=None, md5sum_to=None, diff=False,
             file_status='from'):
    puppetdb_source, puppetdb_certs, puppetdb_verify = get_server(request=request)
    filebucket_source, filebucket_certs, filebucket_verify, filebucket_show = get_server(request=request,
                                                                                         type='filebucket')
    fileserver_source, fileserver_certs, fileserver_verify, fileserver_show = get_server(request=request,
                                                                                         type='fileserver')
    # If Clientbucket is enabled continue else return False

    def fetch_filebucket(url, method):
        headers = {
            'Accept': 's',
        }
        methods = {'get': requests.get,
                   'head': requests.head,
                   }
        if method not in methods:
            print('No can has method: %s' % method)
            return False
        resp = methods[method](url,
                               headers=headers,
                               verify=filebucket_verify,
                               cert=filebucket_certs)
        if resp.status_code != 200:
            return False
        else:
            return resp.text

    def fetch_fileserver(url, method):
        methods = {'get': requests.get,
                   }

        if method not in methods:
            print('No can has method: %s' % method)
            return False
        resp = methods[method](url,
                               verify=fileserver_verify,
                               cert=fileserver_certs)
        if resp.status_code != 200:
            return False
        else:
            return resp.text

    def get_resource(certname, rtype, rtitle):
        resource_params = {
            'query':
                {
                    'operator': 'and',
                    1: '["=", "certname", "' + certname + '"]',
                    2: '["=", "type", "' + rtype + '"]',
                    3: '["=", "title", "' + rtitle + '"]'

                },
        }
        data = pdb_api_get(
            api_url=puppetdb_source,
            path='resources',
            verify=puppetdb_verify,
            cert=puppetdb_certs,
            params=mk_puppetdb_query(resource_params, request))
        if not data:
            return False
        else:
            return data

    if not filebucket_show or not fileserver_source:
        return False
    if file_status == 'both':
        if md5sum_to and md5sum_from and certname and rtitle and rtype:
            if diff:
                # is the hash from puppetdb resource same as md5sum_to
                hash_matches = False

                md5sum_from = md5sum_from.replace('{md5}', '')
                md5sum_to = md5sum_to.replace('{md5}', '')

                from_url = filebucket_source + environment + '/file_bucket_file/md5/' + md5sum_from
                to_url = filebucket_source + environment + '/file_bucket_file/md5/' + md5sum_to

                if fetch_filebucket(from_url, 'head') is not False:
                    resource_from = fetch_filebucket(from_url, 'get')
                else:
                    # Could not find old MD5 in Filebucket
                    return False
                if fetch_filebucket(to_url, 'head') is not False:
                    resource_to = fetch_filebucket(to_url, 'get')
                # Try puppetdb resources if not found in filebucket.
                else:
                    resource_to = get_resource(certname=certname, rtype=rtype, rtitle=rtitle)
                    if resource_to is False:
                        # Could not find new file in Filebucket or as a PuppetDB Resource
                        return False
                    else:
                        resource_to = resource_to[0]
                    if 'content' in resource_to['parameters']:
                        resource_to = resource_to['parameters']['content']
                        hash_of_resource = get_hash(resource_to)
                        if hash_of_resource == md5sum_to:
                            # file from resource matches filebucket md5 hash
                            hash_matches = True
                    # Solve the viewing of source files by retrieving it from Puppetmaster
                    elif 'source' in resource_to['parameters'] and fileserver_show is True:
                        source_path = resource_to['parameters']['source']
                        if source_path.startswith('puppet://'):
                            # extract the path for the file
                            source_path = source_path.split('/')  # ['puppet:', '', '', 'files', 'autofs', 'auto.home']
                            source_path = '/'.join(source_path[3:])  # Skip first 3 entries since they are not needed
                            # https://puppetmaster.example.com:8140/production/file_content/files/autofs/auto.home
                            url = fileserver_source + environment + '/file_content/' + source_path
                            resource_to = fetch_fileserver(url, 'get')
                    else:
                        return False
                # now that we have come this far, we have both files.
                # Lets differentiate the shit out of these files.
                from_split_lines = resource_from.split('\n')
                to_split_lines = resource_to.split('\n')
                diff = difflib.unified_diff(from_split_lines, to_split_lines)
                diff = ('\n'.join(list(diff))).split('\n')
                return diff
            else:
                return False
        else:
            return False

    if file_status == 'from' and md5sum_from:
        md5sum = md5sum_from.replace('{md5}', '')
    elif file_status == 'to' and md5sum_to:
        md5sum = md5sum_to.replace('{md5}', '')
    else:
        return False
    # Creates headers and url from the data we got

    url_clientbucket = filebucket_source + environment + '/file_bucket_file/md5/' + md5sum
    if fetch_filebucket(url_clientbucket, 'head') is False:
        # Check if theres a resource available for the latest file available
        if file_status == 'to':
            resp_pdb = get_resource(certname=certname, rtype=rtype, rtitle=rtitle)
            # we got the data lets give the user the good news.
            if resp_pdb:
                resource_data = resp_pdb[0]
                if 'content' in resource_data['parameters']:
                    prepend_text = 'This file with MD5 %s was found in PuppetDB Resources.\n\n' % (
                        get_hash(resource_data['parameters']['content']))
                    return prepend_text + resource_data['parameters']['content']
                elif 'source' in resource_data['parameters'] and fileserver_show is True:
                    source_path = resource_data['parameters']['source']
                    if source_path.startswith('puppet://'):
                        # extract the path for the file
                        source_path = source_path.split('/')  # ['puppet:', '', '', 'files', 'autofs', 'auto.home']
                        source_path = '/'.join(source_path[3:])  # Skip first 3 entries since they are not needed
                        # https://puppetmaster.example.com:8140/production/file_content/files/autofs/auto.home
                        url = fileserver_source + environment + '/file_content/' + source_path
                        source_content = fetch_fileserver(url, 'get')
                        prepend_text = 'This file with MD5 %s was retrieved from the PuppetMaster Fileserver.\n\n' % (
                            get_hash(source_content))
                        return prepend_text + source_content
                    else:
                        return False
                else:
                    return False
            # the file can't be found as a resource and or fileserver support not enabled
            else:
                return False
        # We probably don't want to search for resources if its the old file.
        else:
            return False
    else:
        filebucket_results = fetch_filebucket(url_clientbucket, 'get')
        prepend_text = 'This file with MD5 %s was found in Filebucket.\n\n' % (md5sum)
        return prepend_text + filebucket_results
