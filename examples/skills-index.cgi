#!/usr/bin/perl
#
# CGI script that generates /.well-known/agent-skills/index.json
# A throwback to simpler times. Works with Apache, Nginx (via fcgiwrap), or any CGI-capable server.
#
# Scans the skills directory for subdirectories, parses YAML frontmatter
# from each SKILL.md, computes SHA-256 digests, and outputs a JSON index
# per the Agent Skills Discovery spec (v0.2.0).
#
# This implementation generates `type: "skill-md"` entries only. Archive-based
# skills (`type: "archive"`) require separate tooling to create and register.
#
# Usage: Place in cgi-bin/ and configure your server to serve it at /.well-known/agent-skills/index.json
# Skills: Place skill directories at /var/www/html/.well-known/agent-skills/{name}/SKILL.md
#
# Note: Only single-line name/description values are supported (no YAML multi-line syntax)
#
# Requires: Perl (comes with your OS since 1987), Digest::SHA (core since Perl 5.9.3)
#
use strict;
use warnings;
use Digest::SHA qw(sha256_hex);
use JSON::PP;

# Configure this path to match your setup
my $skills_dir = $ENV{SKILLS_DIR} || '/var/www/html/.well-known/agent-skills';
my $schema_uri = 'https://schemas.agentskills.io/discovery/0.2.0/schema.json';

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
        my ($name, $description);
        my $content;
        if (open(my $fh, '<:raw', $skill_md)) {
            local $/;
            $content = <$fh>;
            close($fh);

            my $text = $content;
            utf8::decode($text);

            my $in_frontmatter = 0;
            for my $line (split /\n/, $text) {
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
        }

        unless ($name && $description) {
            warn "Skill $entry missing required frontmatter (name/description)\n";
            next;
        }

        # Compute SHA-256 of the SKILL.md file
        my $digest = "sha256:" . sha256_hex($content);

        push @skills, {
            name        => $name,
            type        => 'skill-md',
            description => $description,
            url         => "/.well-known/agent-skills/$entry/SKILL.md",
            digest      => $digest,
        };
    }
    closedir($dh);
} else {
    # Directory doesn't exist - return empty array
    print encode_json({ '$schema' => $schema_uri, skills => [] });
    exit 0;
}

# Sort alphabetically by name
@skills = sort { $a->{name} cmp $b->{name} } @skills;

# Ensure consistent field ordering in JSON output
my $json = JSON::PP->new->canonical(1);
print $json->encode({ '$schema' => $schema_uri, skills => \@skills });
