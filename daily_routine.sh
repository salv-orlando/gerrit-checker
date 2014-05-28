user_name=$1
password=$2
# check for new changes - ie: submitted since last check - in neutron (including specs)
echo New Neutron patches
gerrit-check --project openstack/neutron-specs openstack/neutron openstack/python-neutronclient --user $user_name --password $password --only-new --peek
# check for specs from my team
echo Team specs
gerrit-check --project openstack/nova-specs openstack/neutron-specs --user $user_name --password $password --owners garyk arosen --peek
# check for patches from my team, and add me as a reviewer
echo Team patches
gerrit-check --project openstack/tempest openstack/nova openstack/neutron openstack/python-neutronclient --user $user_name --password $password --owners garyk arosen --add-reviewer self --peek
# check for neutron patches for vmware plugins, and add me as a reviewer
echo VMware Neutron patches
gerrit-check --project openstack/neutron --user $user_name --password $password --file ^neutron/plugins/vmware.* --exclude-owners $user_name --add-reviewer self --peek
# check for neutron patches touching apis, and add me as a reviewer
echo Neutron API patches
gerrit-check --project openstack/neutron --user $user_name --password $password --file ^neutron/api/.* --exclude-owners $user_name --add-reviewer self --peek
# check for neutron patches touching db package, and add me a reviewer
echo Neutron DB patches
gerrit-check --project openstack/neutron --user $user_name --password $password --file ^neutron/db/.* --exclude-owners $user_name --add-reviewer self --peek
# check for neutron patches still without a reviewer (TODO)
# check for tempest network patches still without a reviewer (TODO)
# check for nova/neutron interface patches still without a reviewer (TODO)
# check for patches where I'm a reviewer but haven't actually reviewed yet
gerrit-check --project openstack/neutron openstack/neutron-specs openstack/python-neutronclient openstack/nova openstack/oslo-incubator openstack/tempest --user $user_name --password $password --file ^neutron/db/.* --exclude-owners $user_name --reviewer self --not-reviewed --peek
# check for patches which I'm reviewing and author has replied, and are now
# waiting for another round of review (TODO)
