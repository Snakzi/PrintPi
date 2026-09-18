<?php

namespace Tests\Feature;

use App\Models\PrintJob;
use App\Models\Spool;
use App\Models\User;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Tests\TestCase;

class SpoolApiTest extends TestCase
{
    use RefreshDatabase;

    protected function setUp(): void
    {
        parent::setUp();
        $this->actingAs(User::factory()->create());
    }

    public function test_store_creates_a_full_spool_with_the_materials_density(): void
    {
        $response = $this->postJson(route('spools.store'), [
            'name' => 'Galaxy Black',
            'vendor' => ' Prusament ',
            'material' => 'PETG',
            'color' => '#1a1a2e',
            'finish' => 'glitter',
            'weight' => 1000,
            'spool_weight' => 190,
            'price' => 29.99,
        ])
            ->assertCreated()
            ->assertJsonPath('data.name', 'Galaxy Black')
            ->assertJsonPath('data.vendor', 'Prusament')
            ->assertJsonPath('data.material', 'PETG')
            ->assertJsonPath('data.finish', 'glitter')
            ->assertJsonPath('data.density', 1.27)
            ->assertJsonPath('data.diameter', 1.75)
            ->assertJsonPath('data.used', 0)
            ->assertJsonPath('data.remaining', 1000)
            ->assertJsonPath('data.loaded', false)
            ->assertJsonPath('data.archived_at', null);

        $this->assertEqualsWithDelta(327_000, $response->json('data.remaining_mm'), 1000);
    }

    public function test_store_takes_a_partly_used_spool_and_an_unknown_material(): void
    {
        $this->postJson(route('spools.store'), ['name' => 'Wood', 'material' => 'PLA Wood', 'weight' => 750, 'remaining' => 320.5, 'density' => 1.1])
            ->assertCreated()
            ->assertJsonPath('data.density', 1.1)
            ->assertJsonPath('data.used', 429.5)
            ->assertJsonPath('data.remaining', 320.5);
    }

    public function test_store_validates_the_fields(): void
    {
        $this->postJson(route('spools.store'), ['name' => '', 'material' => 'PLA', 'color' => 'red', 'finish' => 'velvet', 'diameter' => 9, 'weight' => 0])
            ->assertUnprocessable()
            ->assertJsonValidationErrors(['name', 'color', 'finish', 'diameter', 'weight']);
    }

    public function test_a_plain_spool_has_no_finish_and_an_empty_finish_clears_it(): void
    {
        $this->postJson(route('spools.store'), ['name' => 'Jet Black', 'material' => 'PLA'])
            ->assertCreated()
            ->assertJsonPath('data.finish', null);

        $spool = Spool::factory()->create(['finish' => 'glitter']);

        $this->putJson(route('spools.update', $spool), ['finish' => ''])
            ->assertOk()
            ->assertJsonPath('data.finish', null);
    }

    public function test_index_lists_the_loaded_spool_first(): void
    {
        Spool::factory()->create(['name' => 'Older']);
        Spool::factory()->archived()->create(['name' => 'Empty']);
        Spool::factory()->loaded()->create(['name' => 'In the printer']);
        Spool::factory()->create(['name' => 'Newest']);

        $this->getJson(route('spools.index'))
            ->assertOk()
            ->assertJsonCount(4, 'data')
            ->assertJsonPath('data.0.name', 'In the printer')
            ->assertJsonPath('data.1.name', 'Newest')
            ->assertJsonPath('data.2.name', 'Older')
            ->assertJsonPath('data.3.name', 'Empty');
    }

    public function test_catalog_offers_materials_and_vendors_whose_products_use_known_materials(): void
    {
        $response = $this->getJson(route('spools.catalog'))
            ->assertOk()
            ->assertJsonPath('materials.PLA.density', 1.24)
            ->assertJsonPath('vendors.Prusament.spool_weight', 190)
            ->assertJsonPath('vendors.Prusament.products.0', ['line' => 'PLA', 'name' => 'Galaxy Black', 'material' => 'PLA', 'color' => '#26262e', 'finish' => 'glitter'])
            ->assertJsonPath('vendors.Prusament.products.1', ['line' => 'PLA', 'name' => 'Jet Black', 'material' => 'PLA', 'color' => '#0f0f10'])
            ->assertJsonPath('vendors.Fiberlogy.products.0.weight', 850)
            ->assertJsonPath('finishes', ['glitter']);

        $materials = array_keys($response->json('materials'));
        $finishes = $response->json('finishes');
        foreach ($response->json('vendors') as $vendor => $entry) {
            $this->assertNotEmpty($entry['products'], $vendor);
            foreach ($entry['products'] as $product) {
                $this->assertContains($product['material'], $materials, "{$vendor} {$product['line']} {$product['name']}");
                $this->assertMatchesRegularExpression('/^#[0-9a-f]{6}$/', $product['color'], "{$vendor} {$product['line']} {$product['name']}");
                if (isset($product['finish'])) {
                    $this->assertContains($product['finish'], $finishes, "{$vendor} {$product['line']} {$product['name']}");
                }
            }
        }
    }

    public function test_update_sets_the_remaining_weight_and_archives(): void
    {
        $spool = Spool::factory()->loaded()->create(['weight' => 1000, 'used' => 100]);

        $this->putJson(route('spools.update', $spool), ['remaining' => 640, 'spool_weight' => 250])
            ->assertOk()
            ->assertJsonPath('data.used', 360)
            ->assertJsonPath('data.remaining', 640)
            ->assertJsonPath('data.spool_weight', 250)
            ->assertJsonPath('data.loaded', true);

        $this->putJson(route('spools.update', $spool), ['weight' => 500])
            ->assertOk()
            ->assertJsonPath('data.remaining', 140);

        $this->putJson(route('spools.update', $spool), ['archived' => true])
            ->assertOk()
            ->assertJsonPath('data.loaded', false);
        $this->assertNotNull($spool->fresh()->archived_at);

        $this->putJson(route('spools.update', $spool), ['archived' => false])->assertOk()->assertJsonPath('data.archived_at', null);
    }

    public function test_load_puts_one_spool_into_the_printer_and_unload_takes_it_out(): void
    {
        $first = Spool::factory()->loaded()->create();
        $second = Spool::factory()->archived()->create();

        $this->postJson(route('spools.load', $second))
            ->assertOk()
            ->assertJsonPath('data.loaded', true)
            ->assertJsonPath('data.archived_at', null);
        $this->assertFalse($first->fresh()->loaded);
        $this->assertSame(1, Spool::query()->where('loaded', true)->count());

        $this->postJson(route('spools.unload'))->assertNoContent();
        $this->assertSame(0, Spool::query()->where('loaded', true)->count());
    }

    public function test_destroy_removes_the_spool_and_keeps_its_prints(): void
    {
        $spool = Spool::factory()->create();
        $job = PrintJob::factory()->create(['spool_id' => $spool->id]);

        $this->deleteJson(route('spools.destroy', $spool))->assertNoContent();

        $this->assertDatabaseMissing('spools', ['id' => $spool->id]);
        $this->assertNull($job->fresh()->spool_id);
    }

    public function test_a_print_can_be_moved_to_another_spool_and_takes_its_filament_along(): void
    {
        $from = Spool::factory()->create(['used' => 100]);
        $to = Spool::factory()->create(['used' => 0, 'price' => 20, 'weight' => 1000]);
        $job = PrintJob::factory()->create(['spool_id' => $from->id, 'filament_g' => 12.5]);

        $this->putJson(route('prints.update', $job), ['spool_id' => $to->id])
            ->assertOk()
            ->assertJsonPath('data.spool.id', $to->id)
            ->assertJsonPath('data.spool.name', $to->name)
            ->assertJsonPath('data.filament_cost', 0.25);
        $this->assertSame(87.5, $from->fresh()->used);
        $this->assertSame(12.5, $to->fresh()->used);

        $this->putJson(route('prints.update', $job), ['spool_id' => null])
            ->assertOk()
            ->assertJsonPath('data.spool', null)
            ->assertJsonPath('data.filament_cost', null);
        $this->assertSame(0.0, $to->fresh()->used);

        $this->putJson(route('prints.update', $job), ['spool_id' => 9999])->assertUnprocessable();
    }

    public function test_spools_require_login(): void
    {
        auth()->logout();

        $this->getJson(route('spools.index'))->assertUnauthorized();
    }
}
