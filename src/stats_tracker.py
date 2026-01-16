class StatsTracker:
    def __init__(self):
        self.hits = 0
        self.misses = 0
        self.reaction_times = []
        
    def record_hit(self, reaction_time):
        """Record a successful hit"""
        self.hits += 1
        self.reaction_times.append(reaction_time)
        
    def record_miss(self):
        """Record a miss"""
        self.misses += 1
        
    def get_accuracy(self):
        """Calculate accuracy percentage"""
        total = self.hits + self.misses
        if total == 0:
            return 0.0
        return (self.hits / total) * 100
        
    def get_average_reaction_time(self):
        """Calculate average reaction time"""
        if not self.reaction_times:
            return 0.0
        return sum(self.reaction_times) / len(self.reaction_times)
        
    def reset(self):
        """Reset all statistics"""
        self.hits = 0
        self.misses = 0
        self.reaction_times = []