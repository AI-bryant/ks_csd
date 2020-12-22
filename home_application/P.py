#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import subprocess
import xml.etree.ElementTree as ET
import json
import datetime
import sys
import re

def _now(format="%Y-%m-%d %H:%M:%S"):
    return datetime.datetime.now().strftime(format)

##### 可在脚本开始运行时调用，打印当时的时间戳及PID。
def job_start():
    print ("[%s][PID:%s] job_start" % (_now(), os.getpid()))

##### 可在脚本执行成功的逻辑分支处调用，打印当时的时间戳及PID。
def job_success(msg):
    print ("[%s][PID:%s] job_success:[%s]" % (_now(), os.getpid(), msg))
    sys.exit(0)

##### 可在脚本执行失败的逻辑分支处调用，打印当时的时间戳及PID。
def job_fail(msg):
    print( "[%s][PID:%s] job_fail:[%s]" % (_now(), os.getpid(), msg))
    sys.exit(1)

if __name__ == '__main__':

    job_start()

import os
import subprocess
import xml.etree.ElementTree as ET
import json
import re


def __parse_apache__():
    apache = {}
    httpd = 'httpd'
    httpds = __read_shell_lines__("ps -ef|grep httpd|grep -v grep|awk '{print $8}'").splitlines(False)
    if len(httpds) > 0:
        httpd = httpds[0]
    versions = __read_shell_lines__(httpd + ' -V')
    apache['compile_args'] = __trim_str__(versions)
    server_home = __unquote__(__read_properties_from_lines__(versions, 'HTTPD_ROOT', '='))
    if os.path.isdir(server_home):
        apache['home'] = server_home
    apache['version'] = __read_properties_from_lines__(versions, 'Server version', ':')
    config_file = os.path.join(server_home,
                               __unquote__(
                                   __read_properties_from_lines__(versions, 'SERVER_CONFIG_FILE', '=').replace("'",
                                                                                                               "")))
    apache['ports'] = __parse_ports_config__(config_file, server_home)
    configs = [{'name': 'maxkeepaliverequests', 'isArray': False}, {'name': 'maxclients', 'isArray': False}, {'name': 'customlog', 'isArray': False}]
    config_values = __parse_config__(configs, config_file, server_home)
    apache.update(config_values)
    if apache.has_key('customlog'):
        apache['customlog'] = apache['customlog'].replace('"', '')
        if not apache['customlog'].startswith('/'):
            apache['customlog'] = server_home + '/' + apache['customlog']

    return apache


def __parse_nginx__():
    nginx = {}
    versions = __read_shell_err_lines__('nginx -V')
    if versions.find('/bin/sh') >= 0:
        return nginx
    nginx['compile_args'] = __trim_str__(versions)
    nginx['version'] = __read_properties_from_lines__(versions, 'nginx version', ':')
    server_home = __read_properties_from_lines__(versions, 'prefix', '=', '--').replace("'", "")
    if os.path.isdir(server_home):
        nginx['home'] = server_home
        config_file = __read_properties_from_lines__(versions, 'conf-path', '=', '--').replace("'", "")
        if not os.path.isfile(config_file):
            config_file = os.path.join(server_home, 'conf/nginx.conf')
        nginx['ports'] = __parse_ports_config__(config_file, server_home)

    return nginx


DOMAIN_REG_XMLNS = "{http://xmlns.oracle.com/weblogic/domain-registry}"
DOMAIN_XMLNS = "{http://xmlns.oracle.com/weblogic/domain}"
JDBC_XMLNS = "{http://xmlns.oracle.com/weblogic/jdbc-data-source}"


def __parse_server__(config_root):
    servers = []
    for server_config in config_root.findall(DOMAIN_XMLNS + 'server'):
        server = {'name': __get_xml_node_text__(server_config, DOMAIN_XMLNS + 'name')}
        ssl = __parse_server_ssl__(server_config)
        if ssl is not None:
            server['ssl'] = ssl

        nossl = __parse_server_nossl__(server_config)
        if nossl is not None:
            server['nossl'] = nossl

        __read_jvm_params_from_process__("ps -ef|grep weblogic.Name={0}|grep -v grep".format(server['name']), server)

        servers.append(server)
    return servers


def __parse_machine__(server_config):
    machines = []
    for machine_node in server_config.findall(DOMAIN_XMLNS + 'machine'):
        machine = {'name': machine_node.find(DOMAIN_XMLNS + 'name').text}
        node_mgm_node = machine_node.find(DOMAIN_XMLNS + 'node-manager')
        if node_mgm_node is not None:
            node_addr_node = node_mgm_node.find(DOMAIN_XMLNS + 'listen-address')
            if node_addr_node is not None:
                machine['node_listen_address'] = node_addr_node.text
            node_port_node = node_mgm_node.find(DOMAIN_XMLNS + 'listen-port')
            if node_port_node is not None:
                machine['node_listen_port'] = node_port_node.text
            else:
                machine['node_listen_port'] = '5556'
        machines.append(machine)
    return machines


def __parse_server_nossl__(server_config):
    nossl_node = server_config.find(DOMAIN_XMLNS + 'listen-port-enabled')
    if nossl_node is None or 'true' == nossl_node.text:
        nossl = {'listen_port': __get_xml_node_text__(server_config, DOMAIN_XMLNS + 'listen-port', '7001'),
                 'listen_address': __get_xml_node_text__(server_config, DOMAIN_XMLNS + 'listen-address')}
        return nossl
    return None


def __parse_server_ssl__(server_config):
    ssl_node = server_config.find(DOMAIN_XMLNS + 'ssl')
    if ssl_node is not None:
        ssl_enabled = __get_xml_node_text__(ssl_node, DOMAIN_XMLNS + 'enabled')
        if 'true' == ssl_enabled:
            ssl = {'listen_port': __get_xml_node_text__(ssl_node, DOMAIN_XMLNS + 'listen-port', '7002'),
                   'listen_address': __get_xml_node_text__(ssl_node, DOMAIN_XMLNS + 'listen-address')}
            return ssl
    return None


def __parse_domain__(domain_home):
    domain = {}
    if os.path.isdir(domain_home):
        config_file = os.path.join(domain_home, 'config/config.xml')
        if os.path.isfile(config_file):
            domain['home'] = domain_home
            config_tree = ET.parse(config_file)
            config_root = config_tree.getroot()
            domain['name'] = config_root.find(DOMAIN_XMLNS + 'name').text
            domain['version'] = config_root.find(DOMAIN_XMLNS + 'domain-version').text
            domain['servers'] = __parse_server__(config_root)
            domain['machines'] = __parse_machine__(config_root)
            domain['jdbc'] = __parse_jdbc__(config_root, domain_home)

    return domain


def __parse_jdbc__(config_root, domain_home):
    jdbcs = []
    for jdbc_node in config_root.findall(DOMAIN_XMLNS + 'jdbc-system-resource'):
        jdbc = {'name': __get_xml_node_text__(jdbc_node, DOMAIN_XMLNS + 'name'),
                'target': __get_xml_node_text__(jdbc_node, DOMAIN_XMLNS + 'target')}
        jdbc_loc = os.path.join(domain_home, 'config',
                                __get_xml_node_text__(jdbc_node, DOMAIN_XMLNS + 'descriptor-file-name'))
        if os.path.isfile(jdbc_loc):
            jdbc_tree = ET.parse(jdbc_loc)
            jdbc_params_node = jdbc_tree.find(JDBC_XMLNS + 'jdbc-driver-params')
            if jdbc_params_node is not None:
                jdbc['url'] = __get_xml_node_text__(jdbc_params_node, JDBC_XMLNS + 'url')
                matchObj = re.search(r'jdbc:.*://(.*):[0-9]*/([^\?]*)\??.*', jdbc['url'], re.I)
                if matchObj:
                    jdbc['address'] = matchObj.group(1)
                    jdbc['service'] = matchObj.group(2)
                jdbc_properties_node = jdbc_params_node.find(JDBC_XMLNS + 'properties')
                if jdbc_properties_node is not None:
                    for jdbc_property_node in jdbc_properties_node.findall(JDBC_XMLNS + 'property'):
                        if __get_xml_node_text__(jdbc_property_node, JDBC_XMLNS + 'name') == 'user':
                            jdbc['user'] = __get_xml_node_text__(jdbc_property_node, JDBC_XMLNS + 'value')
                            break
            jdbc_pool_node = jdbc_tree.find(JDBC_XMLNS + 'jdbc-connection-pool-params')
            if jdbc_pool_node is not None:
                jdbc['initial-capacity'] = __get_xml_node_text__(jdbc_pool_node, JDBC_XMLNS + 'initial-capacity')
                jdbc['max-capacity'] = __get_xml_node_text__(jdbc_pool_node, JDBC_XMLNS + 'max-capacity')
                jdbc['min-capacity'] = __get_xml_node_text__(jdbc_pool_node, JDBC_XMLNS + 'min-capacity')
            jdbc_datasource_node = jdbc_tree.find(JDBC_XMLNS + 'jdbc-data-source-params')
            if jdbc_datasource_node is not None:
                jdbc['jndi-name'] = __get_xml_node_text__(jdbc_datasource_node, JDBC_XMLNS + 'jndi-name')
        jdbcs.append(jdbc)
    return jdbcs


def __parse_weblogic__():
    admin_lines = __read_shell_lines__(
        "ps -ef|grep java|awk -F \"-Dweblogic.Name=\" '{print $2}'|awk -F \" \" '{print $1}'")
    server_process = __read_shell_single_line__("ps -ef|grep weblogic.home|grep -v grep")
    server_home = __read_properties_from_lines__(server_process, 'weblogic.home', '=', '-D')
    if server_home.endswith(' weblogic.Server'):
        server_home = server_home[0: len(server_home) - 16].strip()

    weblogic = {}

    weblogic['isAdmin'] = admin_lines
    if len(server_home) > 0 and os.path.isdir(server_home):
        home_script = os.path.join(server_home, '../common/bin/commEnv.sh')
        env_script = os.path.join(server_home, '../server/bin/setWLSEnv.sh')
        if os.path.isfile(env_script):
            version_lines = __read_shell_lines__(". {0};java weblogic.version".format(__escape_path__(env_script)))
            matchObj = re.findall(r'weblogic server ([^ ]*) ', version_lines, re.M | re.I)
            if matchObj:
                weblogic['versions'] = matchObj
        if os.path.isfile(home_script):
            mw_home = __read_shell_single_line__(". {0};echo $MW_HOME".format(__escape_path__(home_script)))
        else:
            mw_home = os.path.join(server_home, '../..')
        if len(mw_home) > 0 and os.path.isdir(mw_home):
            domain_reg_file = os.path.join(mw_home, 'domain-registry.xml')
            if os.path.isfile(domain_reg_file):
                domain_tree = ET.parse(domain_reg_file)
                domain_tree_root = domain_tree.getroot()
                domains = []
                for domain in domain_tree_root.findall(DOMAIN_REG_XMLNS + 'domain'):
                    domain_home = domain.get('location')
                    domains.append(__parse_domain__(domain_home))
                weblogic['domains'] = domains

    return weblogic


def __parse_tomcat__():
    server_home = __read_shell_single_line__(
        "ps -ef|grep catalina.home|grep -v grep|grep -v awk|awk -F\"-D\" '{for (i=1;i<=NF;++i){if(match($i,\"catalina.home\")>0){print $i;exit(0)}}}'|awk -F\"=\" '{print $2}'")

    tomcat = {}
    if len(server_home) > 0 and os.path.isdir(server_home):
        tomcat['home'] = server_home
        version_script = os.path.join(server_home, 'bin/version.sh')
        if os.path.isfile(version_script):
            version = __read_shell_lines__("sh {0}".format(__escape_path__(version_script)))
            tomcat['version'] = __read_properties_from_lines__(version, 'Server version', ':')
            tomcat['jdk_version'] = __read_properties_from_lines__(version, 'JVM Version', ':')

        __read_jvm_params_from_process__("ps -ef|grep catalina.home|grep -v grep", tomcat, False)

        config_file = os.path.join(server_home, 'conf/server.xml')
        if os.path.isfile(config_file):
            config_root = ET.parse(config_file).getroot()
            if config_root is not None:
                services = []
                for service_node in config_root.findall('Service'):
                    service = {'name': service_node.get('name')}
                    ports = []
                    for connector_node in service_node.findall('Connector'):
                        port = {'port': connector_node.get('port'), 'protocol': connector_node.get('protocol')}
                        ports.append(port)
                    service['ports'] = ports
                    services.append(service)
                tomcat['services'] = services
    return tomcat


def __read_shell_err_lines__(command):
    process = subprocess.Popen(command, shell=True, stderr=subprocess.PIPE, universal_newlines=True)
    ret = ''
    lines = process.stderr.readlines()
    for line in lines:
        ret += line
    return ret.strip()


def __read_shell_lines__(command):
    process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, universal_newlines=True)
    ret = ''
    lines = process.stdout.readlines()
    for line in lines:
        ret += line
    return ret.strip()


# delete last \n
# trim
# replace double quote with single quote
def __trim_str__(arg):
    ret = arg
    if isinstance(arg, str):
        if arg.endswith('\n'):
            ret = arg[0:len(arg) - 1]
        ret = ret.strip()
        ret = ret.replace('"', "'")
    return ret


def __read_properties_from_lines__(source, tag, split_char, wrap_char='\n'):
    source_lines = source.split(wrap_char)
    for line in source_lines:
        if line.find(tag) >= 0:
            splits = line.split(split_char)
            if len(splits) > 1:
                return splits[1].strip()
    return ''


def __unquote__(s):
    if (s.startswith("'") and s.endswith("'")) or (s.startswith('"') and s.endswith('"')):
        return s[1:len(s) - 1]
    return s


def __parse_ports_config__(config_file, server_home):
    ports = []
    if os.path.isfile(config_file):
        config = __parse__properties__(config_file)
        if config.has('listen'):
            ports.extend(config.get('listen'))
        if config.has('include'):
            for include_config in config.get('include'):
                if include_config.find("*") >= 0:
                    files = __read_shell_lines__(
                        "ls " + __escape_path__(os.path.join(server_home, include_config))).split('\n')
                    for ext_config_file in files:
                        ports.extend(__parse_ports_config__(ext_config_file.strip(), server_home))
                else:
                    ports.extend(__parse_ports_config__(os.path.join(server_home, include_config), server_home))

    return ports


def __parse_config__(configs, config_file, server_home):
    __result = {}
    for key in configs:
        if key['isArray']:
            __result[key['name']] = []

    if os.path.isfile(config_file):
        config = __parse__properties__(config_file)
        for key in configs:
            if config.has(key['name']):
                if key['isArray']:
                    __result[key['name']].extend(config.get(key['name']))
                else:
                    __result[key['name']] = config.get(key['name'])[0]
        if config.has('include'):
            for include_config in config.get('include'):
                if include_config.find("*") >= 0:
                    files = __read_shell_lines__(
                        "ls " + __escape_path__(os.path.join(server_home, include_config))).split('\n')
                    for ext_config_file in files:
                        sub_result = __parse_config__(configs, ext_config_file.strip(), server_home)
                        for key in configs:
                            if sub_result.has_key(key['name']):
                                if key['isArray']:
                                    __result[key['name']].extend(sub_result[key['name']])
                                else:
                                    __result[key['name']] = sub_result[key['name']]
                else:
                    sub_result = __parse_config__(configs, os.path.join(server_home, include_config), server_home)
                    for key in configs:
                        if sub_result.has_key(key['name']):
                            if key['isArray']:
                                __result[key['name']].extend(sub_result[key['name']])
                            else:
                                __result[key['name']] = sub_result[key['name']]

    return __result


class Properties:

    def __init__(self, file_name):
        self.file_name = file_name
        self.properties = {}
        try:
            fopen = open(self.file_name, 'r')
            for line in fopen:
                line = line.strip()
                if line.find('=') > 0 and not line.startswith('#'):
                    strs = line.split('=')
                    key = strs[0].strip().lower()
                    if not self.properties.has_key(key):
                        self.properties[key] = []
                    self.properties[key].append(strs[1].strip())
                elif line.find(' ') > 0 and not line.startswith('#'):
                    strs = line.split(' ')
                    key = strs[0].strip()
                    if key == 'IncludeOptional':
                        key = 'include'
                    key = key.lower()
                    if not self.properties.has_key(key):
                        self.properties[key] = []
                    for index in range(1, len(strs)):
                        if '' != strs[index].strip():
                            value = strs[index].strip();
                            if value.endswith(';'):
                                value = value[0: len(value) - 1]
                            self.properties[key].append(value)
                            break
        except Exception, e:
            raise e
        else:
            fopen.close()

    def has(self, key):
        return self.properties.has_key(key)

    def get(self, key, default_value=''):
        if self.properties.has_key(key):
            return self.properties[key]
        return default_value


def __parse__properties__(file_name):
    return Properties(file_name)


def __escape_path__(path):
    return path.replace(",", "\\'").replace('"', '\\"').replace(' ', '\\ ')


def __get_xml_node_text__(parent_node, tag_name, default=''):
    node = parent_node.find(tag_name)
    if node is not None and node.text is not None:
        return node.text
    else:
        return default


def __read_jvm_params_from_process__(command, result_dict, need_jdk_version=True):
    server_process = __read_shell_single_line__(command)
    if len(server_process) > 0:
        server_args = server_process.split()
        for server_arg in server_args:
            if server_arg.startswith('-Xms'):
                result_dict['Xms'] = __trim_str__(server_arg[4:len(server_arg)])
            if server_arg.startswith('-Xmx'):
                result_dict['Xmx'] = __trim_str__(server_arg[4:len(server_arg)])
            if server_arg.startswith('-XX:PermSize='):
                result_dict['PermSize'] = __trim_str__(server_arg[13:len(server_arg)])
            if server_arg.startswith('-XX:MaxPermSize='):
                result_dict['MaxPermSize'] = __trim_str__(server_arg[16:len(server_arg)])
            if server_arg.endswith('/bin/java') and need_jdk_version:
                result_dict['jdk_version'] = __read_shell_err_lines__(__escape_path__(server_arg) + ' -version')


def __read_shell_single_line__(command):
    process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, universal_newlines=True)
    ret = process.stdout.readline()
    return ret.strip()


result = {'weblogic': __parse_weblogic__(), 'tomcat': __parse_tomcat__(), 'apache': __parse_apache__(),
          'nginx': __parse_nginx__()}

print (json.dumps(result))

