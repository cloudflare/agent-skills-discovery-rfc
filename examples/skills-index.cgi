#!/usr/bin/perl
#
# CGI script that generates /.well-known/agent-skills/index.json
# A throwback to simpler times. Works with Apache, Nginx (via fcgiwrap), or any CGI-capable server.
#
# Scans the skills directory for subdirectories, parses YAML frontmatter
# from each SKILL.md, collects all files with SHA-256 digests, and outputs
# a JSON index per the Agent Skills Discovery spec (v0.2.0).
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
use File::Find;
use Digest::SHA qw(sha256_hex);
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
        my ($name, $description);
        if (open(my $fh, '<', $skill_md)) {
            my $in_frontmatter = 0;

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
        }

        unless ($name && $description) {
            warn "Skill $entry missing required frontmatter (name/description)\n";
            next;
        }

        # Collect all files with digests
        my @files;
        find({
            no_chdir => 1,
            wanted => sub {
                return unless -f $_;
                return if -l $_;  # Skip symlinks

                my $rel = $File::Find::name;
                $rel =~ s/^\Q$skill_path\E\///;

                # Read file and compute SHA-256
                if (open(my $ffh, '<:raw', $_)) {
                    local $/;
                    my $content = <$ffh>;
                    close($ffh);

                    push @files, {
                        path   => $rel,
                        digest => "sha256:" . sha256_hex($content),
                    };
                }
            },
        }, $skill_path);

        # Sort: SKILL.md first, then alphabetically by path
        my @sorted = sort {
            ($a->{path} eq 'SKILL.md') ? -1 :
            ($b->{path} eq 'SKILL.md') ?  1 :
            $a->{path} cmp $b->{path}
        } @files;

        # Compute skill-level digest from sorted file entries
        my @manifest_sorted = sort { $a->{path} cmp $b->{path} } @files;
        my $manifest = join('', map {
            my $hex = $_->{digest};
            $hex =~ s/^sha256://;
            "$_->{path}\0$hex\n"
        } @manifest_sorted);
        my $skill_digest = "sha256:" . sha256_hex($manifest);

        push @skills, {
            name        => $name,
            description => $description,
            digest      => $skill_digest,
            files       => \@sorted,
        };
    }
    closedir($dh);
} else {
    # Directory doesn't exist - return empty array
    print encode_json({ version => '0.2.0', skills => [] });
    exit 0;
}

# Sort alphabetically by name
@skills = sort { $a->{name} cmp $b->{name} } @skills;

print encode_json({ version => '0.2.0', skills => \@skills });
