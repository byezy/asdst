import arcpy as ap
from os.path import split, join
import log
import configure
import project
import utils


class ContextCalculationTool(object):

    class ToolValidator(object):
        """Class for validating a tool's parameter values and controlling
        the behavior of the tool's dialog."""

        def __init__(self, parameters):
            """Setup arcpy and the list of tool parameters."""
            self.params = parameters

        def initializeParameters(self):
            """Refine the properties of a tool's parameters.  This method is
            called when the tool is opened."""
            return

        def updateParameters(self):
            """Modify the values and properties of parameters before internal
            validation is performed.  This method is called whenever a parameter
            has been changed."""
            return

        def updateMessages(self):
            """Modify the messages created by internal validation for each tool
            parameter.  This method is called after internal validation."""
            return

    @log.log
    def __init__(self):

        self.label = u'Calculate Context'
        self.description = u'Calculate project context data'
        self.canRunInBackground = True

        return

    @log.log
    def getParameterInfo(self):

        empty_poly_layer = configure.get_asdst_config().empty_polyf_layer

        # Name
        param_1 = ap.Parameter()
        param_1.name = u'Name'
        param_1.displayName = u'Name'
        param_1.parameterType = 'Required'
        param_1.direction = 'Input'
        param_1.datatype = u'String'

        # Description
        param_2 = ap.Parameter()
        param_2.name = u'Description'
        param_2.displayName = u'Description'
        param_2.parameterType = 'Required'
        param_2.direction = 'Input'
        param_2.datatype = u'String'

        # Context_Feature
        param_3 = ap.Parameter()
        param_3.name = u'Context_Feature'
        param_3.displayName = u'Context Feature'
        param_3.parameterType = 'Required'
        param_3.direction = 'Input'
        param_3.datatype = u'Feature Set'
        param_3.value = empty_poly_layer

        # Assessment_Feature
        param_4 = ap.Parameter()
        param_4.name = u'Assessment_Feature'
        param_4.displayName = u'Assessment Feature'
        param_4.parameterType = 'Required'
        param_4.direction = 'Input'
        param_4.datatype = u'Feature Set'
        param_4.value = empty_poly_layer

        # Conservation_Feature
        param_5 = ap.Parameter()
        param_5.name = u'Conservation_Feature'
        param_5.displayName = u'Conservation Feature'
        param_5.parameterType = 'Required'
        param_5.direction = 'Input'
        param_5.datatype = u'Feature Set'
        param_5.value = empty_poly_layer

        return [param_1, param_2, param_3, param_4, param_5]

    def isLicensed(self):

        return True

    def updateParameters(self, parameters):

        validator = getattr(self, 'ToolValidator', None)
        if validator:
            return validator(parameters).updateParameters()

    def updateMessages(self, parameters):

        validator = getattr(self, 'ToolValidator', None)
        if validator:
            return validator(parameters).updateMessages()

    @log.log
    def execute(self, parameters, messages):
        # Aliases
        add_message = messages.addMessage
        add_error = messages.addErrorMessage

        # Get user inputs
        raw_title = parameters[0].valueAsText  # title
        description = parameters[1].valueAsText  # description
        geom_context = parameters[2].value  # geom (feature set)
        geom_assessment = parameters[3].value  # geom (feature set)
        geom_conservation = parameters[4].value  # geom (feature set)
        sane_title = raw_title.lower().replace(" ", "_")
        mxd = ap.mapping.MapDocument("CURRENT")
        mxd_path = mxd.filePath
        gdb_path = split(mxd_path)[0]
        gdb_name = "context_{0}".format(sane_title) + ".gdb"
        gdb = join(gdb_path, gdb_name)

        table_summ = join(gdb, "loss_summary")
        table_ahims = join(gdb, "ahims_summary")
        context = join(gdb, "context_{0}".format(sane_title))
        assessment = join(gdb, "assessment_{0}".format(sane_title))
        conservation = join(gdb, "conservation_{0}".format(sane_title))

        areas = {"Context": [context, geom_context],
                 "Assessment": [assessment, geom_assessment],
                 "Conservation": [conservation, geom_conservation]}

        config = configure.get_asdst_config(messages)
        proj = project.Project()

        # Make the required file system
        ap.Copy_management(config.template_context_gdb, gdb)
        add_message("Context geodatabase '{0}' created".format(gdb))

        # Import calculation areas into project workspace i.e. save the geometry to be used
        m = "{0} area imported: {1} ({2} - {3})"
        for k, v in areas.iteritems():
            try:
                # might be a feature set
                v[1].save(v[0])
                msg = m.format(k, v[0], "New Feature set", "in_memory")
                add_message(msg)
            except:
                try:
                    # or might be a layer
                    ap.CopyFeatures_management(v[1], v[0])
                    msg = m.format(k, v[0], "Feature layer", v[1])
                    add_message(msg)
                except Exception as e:
                    # or fuck knows what it is
                    add_error("Could not copy aoi geometry {0}".format(e.message))
                    raise ap.ExecuteError

        # Build loss data
        add_message("Getting layer dictionary...")
        layer_dict = config.layer_dictionary(proj.gdb)

        # Calc stats
        add_message("Calculating statistics...")
        n = 0
        res_tot = []
        for k, v in layer_dict.iteritems():
            n += 1
            res = [n]
            res2 = [n]
            res.extend([k, config.codes[k]])  # model_code, model_desc
            res2.extend([k, config.codes[k]])  # model_code, model_desc
            lyr = v["name"]
            add_message("...{0}".format(lyr))
            lyr = v["1750_local"]
            # context
            tmp_ras = join(gdb, "context_{0}_1750".format(k))
            ap.Clip_management(lyr, "#", tmp_ras, context, "#", "ClippingGeometry")
            sumcont1750 = ap.RasterToNumPyArray(tmp_ras, nodata_to_value=0).sum()
            res.append(sumcont1750)  # context_sum_1750
            lyr = v["curr_local"]
            tmp_ras = join(gdb, "context_{0}_curr".format(k))
            ap.Clip_management(lyr, "#", tmp_ras, context, "#", "ClippingGeometry")
            sumcontcurr = ap.RasterToNumPyArray(tmp_ras, nodata_to_value=0).sum()
            res.append(sumcontcurr)  # context_sum_current
            sumchange = (sumcontcurr - sumcont1750)
            res.append(sumchange)  # context_change
            if sumcont1750 == 0:
                loss = 0
            elif sumchange == sumcont1750:
                loss = 100
            else:
                loss = int(-sumchange * 100.0 / sumcont1750)
            res.append(loss)  # context_loss

            # assessment
            tmp_ras = join(gdb, "assessment_{0}_curr".format(k))
            ap.Clip_management(lyr, "#", tmp_ras, assessment, "#", "ClippingGeometry")
            sumass = ap.RasterToNumPyArray(tmp_ras, nodata_to_value=0).sum()
            res.append(sumass)  # assessment_sum
            if sumcontcurr == 0:
                pcass = 0
            else:
                pcass = int(sumass * 100.0 / sumcontcurr)
            res.append(pcass)  # assessment_pc

            # conservation
            tmp_ras = join(gdb, "conservation_{0}_curr".format(k))
            ap.Clip_management(lyr, "#", tmp_ras, conservation, "#", "ClippingGeometry")
            sumcons = ap.RasterToNumPyArray(tmp_ras, nodata_to_value=0).sum()
            res.append(sumcons)  # conservation_sum
            if sumcontcurr == 0:
                pccons = 0
            else:
                pccons = int(sumcons * 100.0 / sumcontcurr)
            res.append(pccons)  # conservation_pc

            res_tot.append(res)

        ic = ap.da.InsertCursor(table_summ, "*")
        for r in res_tot:
            ic.insertRow(r)
        del ic

        # Build AHIMS data if configured
        if config.ahims_sites:
            add_message("Analysing AHIMS points...")
            res_tot = []
            n = 0
            for k, v in config.codes_ex.iteritems():
                add_message("...{0}".format(v))
                n += 1
                res = [n]
                res.extend([k, config.codes_ex[k]])  # model_code, model_desc

                tmp_fc = join(gdb, "ahims_{0}_context".format(k))
                if config.ahims_sites:
                    ap.Intersect_analysis([config.ahims_sites, context], tmp_fc)
                    sc = ap.da.SearchCursor(tmp_fc, "*", '"{0}" IS NOT NULL'.format(k))
                    l = [r for r in sc]
                    res.append(len(l))  # context_pts
                else:
                    res.append(None)

                tmp_fc = join(gdb, "ahims_{0}_assessment".format(k))
                if config.ahims_sites:
                    ap.Intersect_analysis([config.ahims_sites, assessment], tmp_fc)
                    sc = ap.da.SearchCursor(tmp_fc, "*", '"{0}" IS NOT NULL'.format(k))
                    l = [r for r in sc]
                    res.append(len(l))  # context_pts
                else:
                    res.append(None)

                tmp_fc = join(gdb, "ahims_{0}_conservation".format(k))
                if config.ahims_sites:
                    ap.Intersect_analysis([config.ahims_sites, conservation], tmp_fc)
                    sc = ap.da.SearchCursor(tmp_fc, "*", '"{0}" IS NOT NULL'.format(k))
                    l = [r for r in sc]
                    res.append(len(l))  # conservation_pts
                    del sc
                else:
                    res.append(None)

                res_tot.append(res)

            ic = ap.da.InsertCursor(table_ahims, "*")
            for r in res_tot:
                ic.insertRow(r)
            del ic

        # Compact the FGDB workspace
        add_message(utils.compact_fgdb(gdb))  # note the side effect

        # Add data to map
        add_message("Adding feature layers to map...")
        lyrs = {k: v[0] for k, v in areas.iteritems()}
        utils.add_layers_to_mxd(lyrs, "Context {}".format(sane_title), "calc", None, config, messages)
        add_message("Adding result tables to map...")
        utils.add_table_to_mxd(mxd, table_summ, "context_loss", messages)
        utils.add_table_to_mxd(mxd, table_ahims, "context_ahims",messages)

        # Save and report status
        mxd.save()
        add_message("Context calculation {0} successful ({1})".format(raw_title, gdb))

