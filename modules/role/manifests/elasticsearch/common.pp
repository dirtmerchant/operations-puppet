#
# This class configures elasticsearch
#
# == Parameters:
# [*ferm_srange*]
#   The network range that should be allowed access to elasticsearch. This
#   needs to be customized for elasticsearch clusters serving non production
#   traffic. The relforge cluster is an example.
#   Default: $DOMAIN_NETWORKS
#
class role::elasticsearch::common(
    $ferm_srange      = '$DOMAIN_NETWORKS',
) {

    if ($::realm == 'production' and hiera('elasticsearch::rack', undef) == undef) {
        fail("Don't know rack for ${::hostname} and rack awareness should be turned on")
    }

    if ($::realm == 'labs' and hiera('elasticsearch::cluster_name', undef) == undef) {
        $msg = '\$::elasticsearch::cluster_name must be set to something unique to the labs project.'
        $msg2 = 'You can set it in the hiera config of the project'
        fail("${msg}\n${msg2}")
    }

    if hiera('has_lvs', true) {
        include ::lvs::realserver
    }

    ferm::service { 'elastic-http':
        proto   => 'tcp',
        port    => '9200',
        notrack => true,
        srange  => $ferm_srange,
    }

    $elastic_nodes = hiera('elasticsearch::cluster_hosts')
    $elastic_nodes_ferm = join($elastic_nodes, ' ')

    ferm::service { 'elastic-inter-node':
        proto   => 'tcp',
        port    => '9300',
        notrack => true,
        srange  => "@resolve((${elastic_nodes_ferm}))",
    }

    system::role { 'role::elasticsearch::server':
        ensure      => 'present',
        description => 'elasticsearch server',
    }

    package { 'elasticsearch/plugins':
        provider => 'trebuchet',
    }

    # Install
    class { '::elasticsearch':
        require                    => Package['elasticsearch/plugins'],
        # Production elasticsearch needs these plugins to be loaded in order
        # to work properly.  This will keep elasticsearch from starting
        # if these plugins are  not available.
        plugins_mandatory          => [
            'experimental-highlighter',
            'extra',
            'analysis-icu',
        ],
        # Let apifeatureusage create their indices
        auto_create_index          => '+apifeatureusage-*,-*',
        # Production can get a lot of use out of the filter cache.
        filter_cache_size          => '20%',
        bulk_thread_pool_executors => 6,
        bulk_thread_pool_capacity  => 1000,
        # Use only 1 merge thread (instead of 3) to avoid updates interfering with
        # actual searches
        merge_threads              => 1,
    }

    include ::standard
    if $::standard::has_ganglia {
        include ::elasticsearch::ganglia
    }

    class { '::elasticsearch::https':
        ferm_srange => $ferm_srange,
    }
    include elasticsearch::monitor::diamond
    include ::elasticsearch::log::hot_threads

}
