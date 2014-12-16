# vim: set ts=4 et sw=4:

class role::apertium::production {
    system::role { 'role::apertium::production':
        description => 'Apertium APY server'
    }

    include ::apertium

    # Define apertium port
    $apertium_port = '2737'

    # We have to explicitly open the apertium port (bug T47868)
    ferm::service { 'apertium_http':
        proto => 'tcp',
        port  => $apertium_port,
    }

    monitor_service { 'apertium':
        description   => 'apertium apy',
        check_command => 'check_http_on_port!2737',
    }
}

class role::apertium::beta {
    system::role { 'role::apertium::beta':
        description => 'Apertium APY server (on beta)'
    }

    include ::apertium

    # Need to allow jenkins-deploy to reload apertium
    sudo::user { 'jenkins-deploy': privileges => [
        # Since the "root" user is local, we cant add the sudo policy in
        # OpenStack manager interface at wikitech
        'ALL = (root)  NOPASSWD:/usr/sbin/service apertium-apy restart',
    ] }

    # Define Apertium port
    $apertium_port = '2737'

    # We have to explicitly open the apertium port (bug T47868)
    ferm::service { 'apertium_http':
        proto => 'tcp',
        port  => $apertium_port,
    }

    # Allow ssh access from the Jenkins master to the server where apertium is
    # running
    include contint::firewall::labs
}
