"""A plan requests several local choices; unavailable choices are explicit no-ops."""
class Planned:
    def __init__(self,edits):
        self.edits={int(c):int(a) for c,a in edits}
        assert len(self.edits)==len(edits) and all(c>=48 and 1<=a<=3 for c,a in self.edits.items())
        self.visited=[];self.applied=[];self.skipped=[]
    def wants(self,c):return c in self.edits
    def choose(self,x,n,c):
        self.visited.append(c);a=self.edits[c]
        if a>=min(4,n):self.skipped.append(c);return 0
        self.applied.append(c);return a
