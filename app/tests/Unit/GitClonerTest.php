<?php

namespace Tests\Unit;

use App\Exceptions\PluginException;
use App\Services\GitCloner;
use Illuminate\Process\PendingProcess;
use Illuminate\Support\Facades\File;
use Illuminate\Support\Facades\Process;
use Tests\TestCase;

class GitClonerTest extends TestCase
{
    private string $root;

    protected function setUp(): void
    {
        parent::setUp();
        $this->root = sys_get_temp_dir().'/printpi-git-'.uniqid();
        File::ensureDirectoryExists($this->root.'/broken');
    }

    protected function tearDown(): void
    {
        File::deleteDirectory($this->root);
        parent::tearDown();
    }

    public function test_clone_runs_a_shallow_quiet_clone_next_to_the_target(): void
    {
        Process::fake();
        $target = $this->root.'/.clone-abc';

        (new GitCloner)->clone('https://github.com/example/plugin', $target);

        Process::assertRan(fn (PendingProcess $process): bool => $process->command === ['git', 'clone', '--depth', '1', '--quiet', 'https://github.com/example/plugin', $target]
            && $process->path === $this->root
            && $process->environment['GIT_TERMINAL_PROMPT'] === '0');
    }

    public function test_failures_surface_the_last_line_git_printed(): void
    {
        Process::fake(fn () => Process::result('', "fatal: not a git repository\nfatal: cannot pull", 128));

        try {
            (new GitCloner)->pull($this->root.'/broken');
            $this->fail('pull succeeded');
        } catch (PluginException $exception) {
            $this->assertSame('git failed: fatal: cannot pull', $exception->getMessage());
        }
    }
}
