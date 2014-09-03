====================
CloudFoundry Bundle
====================

.. image:: https://badge.fury.io/py/charmgen.png
    :target: http://badge.fury.io/py/charmgen

.. image:: https://travis-ci.org/bcsaller/charmgen.png?branch=master
        :target: https://travis-ci.org/bcsaller/charmgen

.. image:: https://pypip.in/d/charmgen/badge.png
        :target: https://pypi.python.org/pypi/charmgen


A Juju charm to generate CF charms from metadata and
manage them at runtime.

Deployment
----------

If you haven't:

juju bootstrap

Then the following script will create a default settings file:

export ADMIN_PASS=`cat ${JUJU_HOME:-~/.juju}/environments/$(juju switch).jenv|grep admin-secret|awk '{print $2;}'`
cat << EOF > cf.yaml
cloudfoundry:
    admin_secret: $ADMIN_PASS
EOF

And this line will deploy a working cloudfoundry of the latest supported version:

    juju deploy --config cf.yaml local:trusty/cloudfoundry --constraints='root-disk=12G'

This will boot up the bundle orchestrator which will watch and manage a CF
deployment using juju.  (Note: the constraint is required to ensure the orchestrator
has enough disk space for the build artifacts cache.)

Once the deployment is running you will see juju deploy all of the needed
services. When this is going you will be able to

    ENDPOINT=`juju status haproxy/0 |grep public-address|cut -f 2 -d : `
    IP=`dig +short $ENDPOINT`
    # get the _IP_ of the public address
    cf api http://api.${IP}.xip.io
    cf login -u admin -p admin
    cf create-space my-space
    cf target -o my-org -s my-space

You can now push apps.



Development
-----------

For any given release we support (see cloudfoundry.releases) you should be able
to generate an example of the bundle we'll deploy and manage by doing:

    . .tox/py27/bin/activate
    python charmgen/generator.py <release-number>

This will create a cloudfoundry-r<release> directory with the bundle.yaml and a
trusty repo will all the created charms.

There are currently two experimental tools included with the charm. These
are designed to process a cf-release checkout and examine the differences
in various tagged versions of cf-release.

    . .tox/py27/bin/activate
    # skip if you have a cf-release checkout
    git clone https://github.com/cloudfoundry/cf-release.git ../cf-release
    python setup.py develop
    get_revisions -d ../cf-release 153..173
    diff_revisions 153..173 | less

You can also use the following command on the cc unit to monitor the routes
registered with NATS, which can be very helpful for debugging:

    cd /var/vcap/packages/cloud_controller_ng/cloud_controller_ng/vendor/bundle/ruby/1.9.1
    /var/vcap/packages/ruby/bin/bundle exec bin/nats-sub -s `grep -o 'nats://.*' /var/vcap/jobs/cloud_controller_ng/config/cloud_controller_ng.yml` ">"


* TODO

  Attempt to generate service definitions and relation classes from
  cf-release.
