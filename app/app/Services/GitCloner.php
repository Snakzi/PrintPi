<?php

namespace App\Services;

use App\Exceptions\PluginException;
use Illuminate\Support\Facades\Process;

/**
 * The git operations the plugin manager needs, run as the web server user.
 */
class GitCloner
{
    public function clone(string $url, string $target): void
    {
        $this->run(['git', 'clone', '--depth', '1', '--quiet', $url, $target], dirname($target));
    }

    public function pull(string $directory): void
    {
        $this->run(['git', 'pull', '--ff-only', '--quiet'], $directory);
    }

    /**
     * @param  list<string>  $command
     */
    private function run(array $command, string $path): void
    {
        $result = Process::path($path)
            ->timeout(120)
            ->env(['GIT_TERMINAL_PROMPT' => '0', 'HOME' => storage_path('app')])
            ->run($command);
        if ($result->successful()) {
            return;
        }
        $lines = array_values(array_filter(array_map('trim', explode("\n", $result->errorOutput() ?: $result->output()))));

        throw new PluginException('git failed: '.(end($lines) ?: 'exit code '.$result->exitCode()));
    }
}
