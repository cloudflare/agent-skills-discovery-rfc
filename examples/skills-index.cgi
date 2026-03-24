#!/usr/bin/perl
#
# CGI script that generates /.well-known/agent-skills/index.json
# A throwback to simpler times. Works with Apache, Nginx (via fcgiwrap), or any CGI-capable server.
#
# Scans the skills directory for subdirectories, parses YAML frontmatter
# from each SKILL.md, and outputs a JSON index per the Agent Skills Discovery spec.
#
# Usage: Place in cgi-bin/ and configure your server to serve it at /.well-known/agent-skills/index.json
# Skills: Place skill directories at /var/www/html/.well-known/agent-skills/{name}/SKILL.md
#
# Note: Only single-line name/description values are supported (no YAML multi-line syntax)
#
# Requires: Perl (comes with your OS since 1987)
#
use strict;
use warnings;
use JSON::PP;

# Configure this path to match your setup
my $skills_dir = $ENV{SKILLS_DIR} || '/var/www/html/.well-known/agent-skills';

print "Content-Type: application/json\r\n";
print "Cache-Control: public, max-age=300\r\n\r\n";

my @skills;

if (opendir(my $dh, $skills_dir)) {
    while (my $entry = readdir($dh)) {
        next if $entry =~ /^\./;  # Skip hidden files
        my $skill_path = "$skills_dir/$entry";
        next if -l $skill_path;   # Skip symlinks (security)
        next unless -d $skill_path;  # Skip non-directories
        
        my $skill_md = "$skill_path/SKILL.md";
        next unless -f $skill_md;  # Skip if no SKILL.md
        
        # Parse YAML frontmatter
        if (open(my $fh, '<', $skill_md)) {
            my $in_frontmatter = 0;
            my ($name, $description);
            
            while (my $line = <$fh>) {
                chomp $line;
                if ($line eq '---') {
                    if ($in_frontmatter) {
                        last;  # End of frontmatter
                    } else {
                        $in_frontmatter = 1;
                        next;
                    }
                }
                
                if ($in_frontmatter) {
                    if ($line =~ /^name:\s*(.+)$/) {
                        $name = $1;
                        $name =~ s/^["']|["']$//g;  # Strip quotes
                    } elsif ($line =~ /^description:\s*(.+)$/) {
                        $description = $1;
                        $description =~ s/^["']|["']$//g;  # Strip quotes
                    }
                }
            }
            close($fh);
            
            if ($name && $description) {
                push @skills, { name => $name, description => $description };
            } else {
                warn "Skill $entry missing required frontmatter (name/description)\n";
            }
        }
    }
    closedir($dh);
} else {
    # Directory doesn't exist - return empty array
    print encode_json({ skills => [] });
    exit 0;
}

# Sort alphabetically by name
@skills = sort { $a->{name} cmp $b->{name} } @skills;

print encode_json({ skills => \@skills });
