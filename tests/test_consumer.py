import unittest
from resultsdbupdater import consumer as ciconsumer
from os import path
import json
import mock


class FakeHub(object):
    config = {}


@mock.patch('resultsdbupdater.utils.retry_session')
class TestConsumer(unittest.TestCase):
    def setUp(self):
        self.json_dir = path.join(path.abspath(path.dirname(__file__)),
                                  'fake_messages')
        self.consumer = ciconsumer.CIConsumer(FakeHub())
        self.uuid_patcher = mock.patch(
            'resultsdbupdater.utils.uuid.uuid4',
            return_value='1bb0a6a5-3287-4321-9dc5-72258a302a37')
        self.uuid_patcher.start()

    def tearDown(self):
        self.uuid_patcher.stop()

    def test_full_consume_msg(self, mock_get_session):
        mock_rv = mock.Mock()
        mock_rv.status_code = 201
        mock_requests = mock.Mock()
        mock_requests.post.return_value = mock_rv
        mock_get_session.return_value = mock_requests
        fake_msg_path = path.join(self.json_dir, 'message.json')
        with open(fake_msg_path) as fake_msg_file:
            fake_msg = json.load(fake_msg_file)

        assert self.consumer.consume(fake_msg) is True
        # Verify the URLs called
        assert mock_requests.post.call_args_list[0][0][0] == \
            'https://resultsdb.domain.local/api/v2.0/results'
        assert mock_requests.post.call_args_list[1][0][0] == \
            'https://resultsdb.domain.local/api/v2.0/results'
        # Verify the post data
        assert mock_requests.post.call_count == 2
        expected_data_one = {
            'data': {
                'CI_tier': 1,
                'artifact': 'unknown',
                'brew_task_id': 14655525,
                'executed': 6,
                'executor': 'CI_OSP',
                'failed': 2,
                'item': 'libreswan-3.23-0.1.rc1.el6_9',
                'job_name': 'ci-libreswan-brew-rhel-6.9-z-candidate-2-runtest',
                'recipients': ['tbrady', 'rgronkowski'],
                'type': 'koji_build'
            },
            'groups': [{
                'ref_url': 'https://domain.local/job/ci-openstack/5154/',
                'uuid': '1bb0a6a5-3287-4321-9dc5-72258a302a37'
            }],
            'note': '',
            'outcome': 'FAILED',
            'ref_url': 'https://domain.local/job/ci-openstack/5154/console',
            'testcase': {
                'name': ('baseos.ci-libreswan-brew-rhel-6.9-z-candidate-2-'
                         'runtest.CI_OSP'),
                'ref_url': 'https://domain.local/job/ci-openstack/'
            }
        }
        expected_data_two = {
            'data': {
                'CI_tier': 1,
                'artifact': 'unknown',
                'brew_task_id': 14655525,
                'item': 'libreswan-3.23-0.1.rc1.el6_9',
                'job_name': 'ci-libreswan-brew-rhel-6.9-z-candidate-2-runtest',
                'recipients': ['tbrady', 'rgronkowski'],
                'type': 'koji_build'
            },
            'groups': [{
                'ref_url': 'https://domain.local/job/ci-openstack/5154/',
                'uuid': '1bb0a6a5-3287-4321-9dc5-72258a302a37'
            }],
            'note': '',
            'outcome': 'FAILED',
            'ref_url': 'https://domain.local/job/ci-openstack/5154/console',
            'testcase': {
                'name': ('baseos.ci-libreswan-brew-rhel-6.9-z-candidate-2-'
                         'runtest'),
                'ref_url': 'https://domain.local/job/ci-openstack/'
            }
        }
        actual_data_one = json.loads(
            mock_requests.post.call_args_list[0][1]['data'])
        actual_data_two = json.loads(
            mock_requests.post.call_args_list[1][1]['data'])
        assert expected_data_one == actual_data_one, actual_data_one
        assert expected_data_two == actual_data_two, actual_data_two

    def test_full_consume_overall_rpmdiff_msg(self, mock_get_session):
        mock_post_rv = mock.Mock()
        mock_post_rv.status_code = 201
        mock_get_rv = mock.Mock()
        mock_get_rv.status_code = 200
        mock_get_rv.json.return_value = {
            'data': [{
                'description': 'https://domain.local/run/12345',
                'uuid': '529da400-fc74-4b28-af81-52f56816a2cb'
            }]
        }
        mock_requests = mock.Mock()
        mock_requests.post.return_value = mock_post_rv
        mock_requests.get.return_value = mock_get_rv
        mock_get_session.return_value = mock_requests
        fake_msg_path = path.join(self.json_dir, 'rpmdiff_message.json')
        with open(fake_msg_path) as fake_msg_file:
            fake_msg = json.load(fake_msg_file)

        assert self.consumer.consume(fake_msg) is True
        # Assert it checked to see if an existing group exists to add the new
        # result to
        mock_requests.get.assert_called_once_with(
            ('https://resultsdb.domain.local/api/v2.0/groups?description='
             'https://domain.local/run/12345'),
            verify=None
        )
        # Verify the post URL
        assert mock_requests.post.call_args_list[0][0][0] == \
            'https://resultsdb.domain.local/api/v2.0/results'
        # Verify the post data
        assert mock_requests.post.call_count == 1
        expected_data = {
            'data': {
                'item': 'setup-2.8.71-5.el7_1',
                'newnvr': 'setup-2.8.71-5.el7_1',
                'oldnvr': 'setup-2.8.71-5.el7',
                'scratch': True,
                'taskid': 12644803,
                'type': 'koji_build'
            },
            'groups': [{
                'description': 'https://domain.local/run/12345',
                'ref_url': 'https://domain.local/run/12345',
                'uuid': '529da400-fc74-4b28-af81-52f56816a2cb'
            }],
            'note': '',
            'outcome': 'NEEDS_INSPECTION',
            'ref_url': 'https://domain.local/run/12345',
            'testcase': {
                'name': 'dist.rpmdiff.analysis',
                'ref_url': 'https://domain.local/rpmdiff-in-ci'
            }
        }
        assert expected_data == \
            json.loads(mock_requests.post.call_args_list[0][1]['data'])

    def test_full_consume_rpmdiff_msg(self, mock_get_session):
        mock_post_rv = mock.Mock()
        mock_post_rv.status_code = 201
        mock_get_rv = mock.Mock()
        mock_get_rv.status_code = 200
        mock_get_rv.json.return_value = {'data': []}
        mock_requests = mock.Mock()
        mock_requests.post.return_value = mock_post_rv
        mock_requests.get.return_value = mock_get_rv
        mock_get_session.return_value = mock_requests
        fake_msg_path = path.join(self.json_dir, 'rpmdiff_message_two.json')
        with open(fake_msg_path) as fake_msg_file:
            fake_msg = json.load(fake_msg_file)

        assert self.consumer.consume(fake_msg) is True
        # Assert it checked to see if an existing group exists to add the new
        # result to, but this time nothing was returned
        mock_requests.get.assert_called_once_with(
            ('https://resultsdb.domain.local/api/v2.0/groups?description='
             'https://domain.local/run/12345'),
            verify=None
        )
        # Verify the post URL
        assert mock_requests.post.call_args_list[0][0][0] == \
            'https://resultsdb.domain.local/api/v2.0/results'
        # Verify the post data
        assert mock_requests.post.call_count == 1
        expected_data = {
            'data': {
                'item': 'lapack-3.4.2-8.el7 lapack-3.4.2-7.el7',
                'newnvr': 'lapack-3.4.2-8.el7',
                'oldnvr': 'lapack-3.4.2-7.el7',
                'scratch': False,
                'taskid': 12665429,
                'type': 'koji_build_pair'
            },
            'groups': [{'description': 'https://domain.local/run/12345',
                        'ref_url': 'https://domain.local/run/12345',
                        'uuid': '1bb0a6a5-3287-4321-9dc5-72258a302a37'}],
            'note': '',
            'outcome': 'PASSED',
            'ref_url': 'https://domain.local/run/12345/13',
            'testcase': {
                'name': 'dist.rpmdiff.comparison.abi_symbols',
                'ref_url': ('https://domain.local/display/HTD/rpmdiff-abi-'
                            'symbols')
            }
        }
        assert expected_data == \
            json.loads(mock_requests.post.call_args_list[0][1]['data'])

    def test_full_consume_cips_msg(self, mock_get_session):
        mock_post_rv = mock.Mock()
        mock_post_rv.status_code = 201
        mock_requests = mock.Mock()
        mock_requests.post.return_value = mock_post_rv
        mock_get_session.return_value = mock_requests
        fake_msg_path = path.join(self.json_dir, 'cips_message.json')
        with open(fake_msg_path) as fake_msg_file:
            fake_msg = json.load(fake_msg_file)

        assert self.consumer.consume(fake_msg) is True
        # Verify the post URL
        assert mock_requests.post.call_args_list[0][0][0] == \
            'https://resultsdb.domain.local/api/v2.0/results'
        # Verify the post data
        assert mock_requests.post.call_count == 1
        all_expected_data = {}

        all_expected_data = {
            'data': {
                'component': 'setup-2.8.71-7.el7_4',
                'brew_task_id': '15477983',
                'category': 'sanity',
                'item': 'setup-2.8.71-7.el7_4',
                'scratch': True,
                'build_type': 'brew-build',
                'issuer': 'jenkins/domain.local',
                'rebuild': ('https://domain.local/job/ci-package-sanity-development'
                            '/label=ose-slave-tps,provision_arch=x86_64/1835//'
                            'rebuild/parametrized'),
                'log': ('https://domain.local/job/ci-package-sanity-development'
                        '/label=ose-slave-tps,provision_arch=x86_64/1835//console'),
                'system_os': 'rhel-7.4-server-x86_64-updated',
                'system_provider': 'openstack',
                'ci_name': 'RPM Factory',
                'ci_url': 'https://domain.local',
                'ci_environment': 'production',
                'ci_team': 'rpm-factory',
                'ci_irc': '#rpm-factory',
                'ci_email': 'nobody@redhat.com'
            },
            'groups': [
                {
                    'url': ('https://domain.local/job/ci-package-sanity-development'
                            '/label=ose-slave-tps,provision_arch=x86_64/1835/'),
                    'uuid': '1bb0a6a5-3287-4321-9dc5-72258a302a37'
                },
            ],
            'note': '',
            'outcome': 'PASSED',
            'ref_url': ('https://domain.local/job/ci-package-sanity-development'
                        '/label=ose-slave-tps,provision_arch=x86_64/1835/'),
            'testcase': {
                'name': 'cips',
                'ref_url': 'https://domain.local/job/ci-package-sanity-development'
            },
        }

        assert all_expected_data == \
            json.loads(mock_requests.post.call_args_list[0][1]['data'])

    def test_full_consume_covscan_msg(self, mock_get_session):
        mock_post_rv = mock.Mock()
        mock_post_rv.status_code = 201
        mock_get_rv = mock.Mock()
        mock_get_rv.status_code = 200
        mock_get_rv.json.return_value = {'data': []}
        mock_requests = mock.Mock()
        mock_requests.post.return_value = mock_post_rv
        mock_requests.get.return_value = mock_get_rv
        mock_get_session.return_value = mock_requests
        fake_msg_path = path.join(self.json_dir, 'covscan_message.json')
        with open(fake_msg_path) as fake_msg_file:
            fake_msg = json.load(fake_msg_file)

        assert self.consumer.consume(fake_msg) is True
        # Assert it checked to see if an existing group exists to add the new
        # result to, but this time nothing was returned
        mock_requests.get.assert_called_once_with(
            ('https://resultsdb.domain.local/api/v2.0/groups?description='
             'http://domain.local/covscanhub/task/64208/log/added.html'),
            verify=None
        )
        # Verify the post URL
        assert mock_requests.post.call_args_list[0][0][0] == \
            'https://resultsdb.domain.local/api/v2.0/results'
        # Verify the post data
        assert mock_requests.post.call_count == 1
        expected_data = {
            'data': {
                'item': 'ipa-4.5.4-5.el7 ipa-4.5.4-4.el7',
                'newnvr': 'ipa-4.5.4-5.el7',
                'oldnvr': 'ipa-4.5.4-4.el7',
                'scratch': True,
                'taskid': 14655680,
                'type': 'koji_build_pair'
            },
            'groups': [{
                'description': ('http://domain.local/covscanhub/task/64208/log'
                                '/added.html'),
                'ref_url': ('http://domain.local/covscanhub/task/64208/log/'
                            'added.html'),
                'uuid': '1bb0a6a5-3287-4321-9dc5-72258a302a37'
            }],
            'note': '',
            'outcome': 'PASSED',
            'ref_url': ('http://domain.local/covscanhub/task/64208/log/'
                        'added.html'),
            'testcase': {
                'name': 'dist.covscan',
                'ref_url': 'https://domain.local/covscan-in-ci'
            }
        }
        assert expected_data == \
            json.loads(mock_requests.post.call_args_list[0][1]['data'])

    def test_full_consume_bulk_results_msg(self, mock_get_session):
        mock_post_rv = mock.Mock()
        mock_post_rv.status_code = 201
        mock_requests = mock.Mock()
        mock_requests.post.return_value = mock_post_rv
        mock_get_session.return_value = mock_requests
        fake_msg_path = path.join(self.json_dir, 'bulk_results_message.json')
        with open(fake_msg_path) as fake_msg_file:
            fake_msg = json.load(fake_msg_file)

        assert self.consumer.consume(fake_msg) is True
        all_expected_data = {
            'dva.ami.memory': {
                'data': {'item': 'ami-b63769a1'},
                'groups': [{
                    'ref_url': 'http://domain.local/path/to/test',
                    'uuid': '1bb0a6a5-3287-4321-9dc5-72258a302a37'
                }],
                'note': '',
                'outcome': 'PASSED',
                'ref_url': 'http://domain.local/path/to/test/memory',
                'testcase': 'dva.ami.memory'
            },
            'dva.ami.no_avc_denials': {
                'data': {'item': 'ami-b63769a1'},
                'groups': [{
                    'ref_url': 'http://domain.local/path/to/test',
                    'uuid': '1bb0a6a5-3287-4321-9dc5-72258a302a37'
                }],
                'note': '',
                'outcome': 'PASSED',
                'ref_url': ('http://domain.local/path/to/test/'
                            'no_avc_denials_test'),
                'testcase': 'dva.ami.no_avc_denials'
            },
            'dva.ami': {
                'data': {'item': 'ami-b63769a1'},
                'groups': [{
                    'ref_url': 'http://domain.local/path/to/test',
                    'uuid': '1bb0a6a5-3287-4321-9dc5-72258a302a37'
                }],
                'note': '',
                'outcome': 'PASSED',
                'ref_url': 'http://domain.local/path/to/test',
                'testcase': 'dva.ami'
            }
        }
        # We can't guarantee the order of when the results are created, so this
        # is a workaround
        testcase_names = all_expected_data.keys()
        for i in range(len(all_expected_data)):
            post_call_data = json.loads(
                mock_requests.post.call_args_list[i][1]['data'])
            testcase_name = post_call_data['testcase']
            assert post_call_data == all_expected_data[testcase_name]
            testcase_names.pop(testcase_names.index(testcase_name))
        msg = 'Not all the expected testcases were processed'
        assert len(testcase_names) == 0, msg

    def test_full_consume_bogus_msg(self, mock_get_session):
        fake_msg_path = path.join(self.json_dir, 'bogus.json')
        with open(fake_msg_path) as fake_msg_file:
            fake_msg = json.load(fake_msg_file)

        assert self.consumer.consume(fake_msg) is False
        mock_get_session.assert_not_called()
