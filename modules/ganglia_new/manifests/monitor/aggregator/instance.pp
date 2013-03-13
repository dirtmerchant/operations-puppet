define ganglia_new::monitor::aggregator::instance() {
	Ganglia_new::Monitor::Aggregator::Instance[$title] -> Service[ganglia-monitor-aggregator]

	include ganglia_new::configuration, network::constants

	$aggregator = true

	# TODO: support multiple $site
	$cluster = $title
	$id = $ganglia_new::configuration::clusters[$cluster]['id']
	$portnr = $ganglia_new::configuration::base_port + $id
	$gmond_port = $::realm ? {
		production => $portnr,
		labs => $::project_gid
	}
	$cname = "${cluster} ${::site}"

	file { "/etc/ganglia/aggregators/${id}.conf":
		require => File["/etc/ganglia/aggregators"],
		mode => 0444,
		content => template("$module_name/gmond.conf.erb"),
		notify => Service[$title]
	}
}
