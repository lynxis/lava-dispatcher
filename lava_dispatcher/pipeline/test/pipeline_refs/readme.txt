To rebuild and update these pipeline references, use:

    import yaml
    with open('/tmp/test.yaml', 'wb') as describe:
        yaml.dump(self.job.pipeline.describe(False), describe)

Then use:

from lava_dispatcher.pipeline.test.test_basic import pipeline_reference

    # Check Pipeline
    description_ref = pipeline_reference('kexec.yaml')
    self.assertEqual(description_ref, self.job.pipeline.describe(False))

or just

    self.assertEqual(pipeline_reference(filename), self.job.pipeline.describe(False))

The name of the pipeline_ref file should match the name of the equivalent file in sample_jobs.
