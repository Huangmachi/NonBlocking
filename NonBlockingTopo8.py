# Copyright (C) 2016 Huang MaChi at Chongqing University
# of Posts and Telecommunications, China.
# Copyright (C) 2016 Li Cheng at Beijing University of Posts
# and Telecommunications. www.muzixing.com
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from mininet.net import Mininet
from mininet.node import Controller, RemoteController
from mininet.cli import CLI
from mininet.log import setLogLevel
from mininet.link import Link, Intf, TCLink
from mininet.topo import Topo

import logging
import os


class NonBlockingTopo(Topo):
	"""
		Class of NonBlocking Topology.
	"""
	CoreSwitchList = []
	HostList = []

	def __init__(self, k):
		self.pod = k
		self.iCoreLayerSwitch = 1
		self.iHost = k**3/4

		# Init Topo
		Topo.__init__(self)

	def createNodes(self):
		self.createCoreLayerSwitch(self.iCoreLayerSwitch)
		self.createHost(self.iHost)

	def _addSwitch(self, number, level, switch_list):
		"""
			Create switches.
		"""
		for i in xrange(1, number+1):
			PREFIX = str(level) + "00"
			if i >= 10:
				PREFIX = str(level) + "0"
			switch_list.append(self.addSwitch(PREFIX + str(i)))

	def createCoreLayerSwitch(self, NUMBER):
		self._addSwitch(NUMBER, 1, self.CoreSwitchList)

	def createHost(self, NUMBER):
		"""
			Create hosts.
		"""
		for i in xrange(1, NUMBER+1):
			if i >= 100:
				PREFIX = "h"
			elif i >= 10:
				PREFIX = "h0"
			else:
				PREFIX = "h00"
			self.HostList.append(self.addHost(PREFIX + str(i), cpu=1.0/NUMBER))

	def createLinks(self, bw_h2c=10):
		"""
			Add links between switch and hosts.
		"""
		for sw in self.CoreSwitchList:
			for host in self.HostList:
				self.addLink(sw, host, bw=bw_h2c, max_queue_size=1000)   # use_htb=False

	def set_ovs_protocol_13(self):
		"""
			Set the OpenFlow version for switches.
		"""
		self._set_ovs_protocol_13(self.CoreSwitchList)

	def _set_ovs_protocol_13(self, sw_list):
		for sw in sw_list:
			cmd = "sudo ovs-vsctl set bridge %s protocols=OpenFlow13" % sw
			os.system(cmd)


def set_host_ip(net, topo):
	hostlist = []
	for k in xrange(len(topo.HostList)):
		hostlist.append(net.get(topo.HostList[k]))
	i = 1
	for host in hostlist:
		host.setIP("10.0.0.%d" % i)
		i += 1

def install_proactive(net, topo):
	"""
		Install proactive flow entries for the switch.
	"""
	for sw in topo.CoreSwitchList:
		for i in xrange(1, topo.iHost + 1):
			cmd = "ovs-ofctl add-flow %s -O OpenFlow13 \
				'table=0,idle_timeout=0,hard_timeout=0,priority=40,arp, \
				nw_dst=10.0.0.%d,actions=output:%d'" % (sw, i, i)
			os.system(cmd)
			cmd = "ovs-ofctl add-flow %s -O OpenFlow13 \
				'table=0,idle_timeout=0,hard_timeout=0,priority=40,ip, \
				nw_dst=10.0.0.%d,actions=output:%d'" % (sw, i, i)
			os.system(cmd)

def createTopo(pod, ip="192.168.56.101", port=6653, bw_h2c=10):
	"""
		Create network topology and run the Mininet.
	"""
	topo = NonBlockingTopo(pod)
	topo.createNodes()
	topo.createLinks(bw_h2c=bw_h2c)

	# Start Mininet
	CONTROLLER_IP = ip
	CONTROLLER_PORT = port
	net = Mininet(topo=topo, link=TCLink, controller=None, autoSetMacs=True)
	net.addController(
		'controller', controller=RemoteController,
		ip=CONTROLLER_IP, port=CONTROLLER_PORT)
	net.start()

	# Set OVS's protocol as OF13.
	topo.set_ovs_protocol_13()
	# Set hosts IP addresses.
	set_host_ip(net, topo)
	# Install proactive flow entries.
	install_proactive(net, topo)

	CLI(net)
	net.stop()

if __name__ == '__main__':
	setLogLevel('info')
	if os.getuid() != 0:
		logging.debug("You are NOT root")
	elif os.getuid() == 0:
		# createTopo(4)
		createTopo(8)
