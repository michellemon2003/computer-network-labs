from mininet.topo import Topo

class MyTopo( Topo ):
    def build( self ):
      #Creating two switches
      s1 = self.addSwitch( 's1' )
      s2 = self.addSwitch( 's2' )

      #Creating four hosts
      h1 = self.addHost( 'h1' )
      h2 = self.addHost( 'h2' )
      h3 = self.addHost( 'h3' )
      h4 = self.addHost( 'h4' )

      #Link connection
      self.addLink( h1, s1 )
      self.addLink( h2, s1 )
      self.addLink( s1, s2 )
      self.addLink( s2, h3 )
      self.addLink( s2, h4 )


topos = { 'mytopo': ( lambda: MyTopo() ) }