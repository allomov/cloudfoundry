# -*- coding: utf-8 -*-
import os
from itertools import chain

import yaml

from . contexts import OrchestratorRelation


class CharmGenerator(object):
    author = "CloudFoundry Charm Generator <cs:~cf-charmers/cloudfoundry>"

    def __init__(self, releases, service_registry):
        self.__releases = releases
        self.release = None
        self.release_version = None
        self.service_registry = service_registry

    def select_release(self, version):
        if isinstance(version, str):
            try:
                version = int(version)
            except ValueError:
                raise KeyError(version)

        for r in self.__releases:
            versions = r['releases']
            low = versions[0]
            high = None
            if len(versions) == 2:
                high = versions[1]
            if version < low:
                continue
            if not high or version <= high:
                self.release = r
                self.release_version = version
                return r
        raise KeyError(version)

    def build_metadata(self, service_key):
        if not self.release:
            raise ValueError
        # service usage within the topo can include the service name
        # allowing this to be a tuple
        if isinstance(service_key, (tuple, list)):
            service_key = service_key[0]
        service = self.service_registry[service_key]
        result = dict(
            name=service_key,
            summary=service.get('summary', ''),
            description=service.get('description', ''),
            author=self.author,
            requires={
                OrchestratorRelation.name: dict(
                    interface=OrchestratorRelation.interface)
            })
        provides = {}
        for job in service['jobs']:
            for relation in job['provided_data']:
                provides[relation.name] = dict(interface=relation.interface)
            for relation in job['required_data']:
                result['requires'][relation.name] = dict(
                    interface=relation.interface)
        if provides:
            result['provides'] = provides

        return result

    def build_hooks(self, service_key):
        meta = self.build_metadata(service_key)
        results = ['start', 'stop', 'config-changed',
                   'upgrade-charm', 'install']
        for rel in chain(meta.get('provides', {}), meta.get('requires', {})):
            results.append('{}-relation-changed'.format(rel))
            results.append('{}-relation-joined'.format(rel))
            results.append('{}-relation-broken'.format(rel))
        return results

    def build_entry(self, service_key):
        return "\n".join([
            '#!/usr/bin/env python2.7',
            'from cloudfoundry.jobs import job_manager',
            'job_manager("{}")'.format(service_key)
        ])

    def generate_charm(self, service_key, target_dir):
        if not os.path.exists(target_dir):
            os.makedirs(target_dir)
        meta = self.build_metadata(service_key)
        meta_target = open(os.path.join(target_dir, 'metadata.yaml'), 'w')
        yaml.safe_dump(meta, meta_target)
        meta_target.close()

        hook_dir = os.path.join(target_dir, 'hooks')
        os.makedirs(hook_dir)
        entry = os.path.join(target_dir, 'hooks', 'entry.py')

        with open(entry, 'w') as target:
            os.fchmod(target.fileno(), 0755)
            target.write(self.build_entry(service_key))

        for hook in self.build_hooks(service_key):
            os.symlink(entry, os.path.join(hook_dir, hook))

    def _build_charm_ref(self, charm_id):
        if charm_id.startswith('cs:'):
            return dict(charm=charm_id)
        else:
            return dict(branch="local:trusty/{}".format(charm_id))

    def _parse_charm_ref(self, service_id):
        if isinstance(service_id, tuple):
            charm_id = service_id[0]
            service_name = service_id[1]
        else:
            charm_id = service_id
            service_name = service_id

        if '/' in service_name:
            service_name = service_name.split('/', 1)[1]

        return charm_id, service_name

    def build_deployment(self):
        services = {}
        relations = []
        result = {'cloudfoundry': {
            # Trusty is Magic!
            'series': 'trusty',
            'services': services,
            'relations': relations
        }}

        for service_id in self.release['topology']['services']:
            charm_id, service_name = self._parse_charm_ref(service_id)
            services[service_name] = self._build_charm_ref(charm_id)

        rel_data = {}
        for rel in self.release['topology']['relations']:
            lhs = "{}:{}".format(*rel[0])
            rhs = "{}:{}".format(*rel[1])
            rel_data.setdefault(lhs, []).append(rhs)
        for k, v in rel_data.items():
            relations.append((k, tuple(v)))
        return result

    def generate_deployment(self, target_dir):
        if not os.path.exists(target_dir):
            os.makedirs(target_dir)
        bundle = self.build_deployment()
        target = os.path.join(target_dir, 'bundles.yaml')
        with open(target, 'w') as fp:
            yaml.safe_dump(bundle, fp)
            fp.flush()
